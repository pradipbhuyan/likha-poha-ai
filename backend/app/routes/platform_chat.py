"""
platform_chat.py — User-to-user real-time chat
───────────────────────────────────────────────────────────────────────
Endpoints:
  GET  /api/chat/settings           — check if current user can use chat
  GET  /api/chat/contacts           — list users the current user can chat with
  GET  /api/chat/rooms              — list my chat rooms (with last message)
  POST /api/chat/rooms              — get-or-create a room with another user
  GET  /api/chat/rooms/{room_id}/messages  — message history (newest first)
  POST /api/chat/rooms/{room_id}/messages  — send a message
  POST /api/chat/rooms/{room_id}/read      — mark all unread as read
  POST /api/chat/upload                    — get a signed upload URL for attachment
  DELETE /api/chat/messages/{msg_id}       — soft-delete own message

Admin endpoints:
  GET  /api/admin/chat/settings     — get global chat settings
  PUT  /api/admin/chat/settings     — update global chat settings
  GET  /api/admin/chat/users        — list users with chat access
  PATCH /api/admin/chat/users/{user_id}  — grant/revoke chat access
  GET  /api/admin/chat/rooms        — moderation view (all rooms)
  DELETE /api/admin/chat/rooms/{room_id} — deactivate a room (admin moderation)
───────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..services.auth_service import (
    admin_client,
    get_current_user,
    get_user_profile,
    require_admin,
)

router = APIRouter()

# ── Default chat settings ─────────────────────────────────────────────────────
CHAT_SETTINGS_KEY = "platform_chat_settings"
DEFAULT_CHAT_SETTINGS = {
    "global_enabled": True,
    "allow_files": True,
    "allow_voice": True,
    "max_file_size_mb": 10,
    "retention_days": 90,
}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_chat_settings() -> dict:
    """Load platform chat settings from admin_settings. Returns defaults if absent."""
    try:
        row = (
            admin_client.table("admin_settings")
            .select("value")
            .eq("key", CHAT_SETTINGS_KEY)
            .limit(1)
            .execute()
        )
        if row.data:
            return {**DEFAULT_CHAT_SETTINGS, **(row.data[0]["value"] or {})}
    except Exception:
        pass
    return dict(DEFAULT_CHAT_SETTINGS)


def _get_chat_user_ids() -> list:
    """Return list of user IDs that have been explicitly granted chat access."""
    try:
        row = (
            admin_client.table("admin_settings")
            .select("value")
            .eq("key", "chat_access_users")
            .limit(1)
            .execute()
        )
        if row.data:
            return row.data[0].get("value", {}).get("user_ids", [])
    except Exception:
        pass
    return []


def _set_chat_user_ids(user_ids: list) -> None:
    admin_client.table("admin_settings").upsert(
        {"key": "chat_access_users", "value": {"user_ids": user_ids}},
        on_conflict="key",
    ).execute()


def _user_can_chat(user_id: str, profile: dict, settings: dict) -> bool:
    """
    Returns True if the user is allowed to use platform chat.

    Chat is free for every role and plan (student/parent/teacher/admin) — the
    only gate is the admin's global on/off switch. `_get_chat_user_ids` /
    `chat_access_users` (the old per-user allowlist from when chat was a
    paid-only feature) is no longer consulted here; the admin endpoints that
    manage it are kept as-is in case fine-grained control is needed again.
    """
    del user_id, profile  # unused now that chat is free for all — kept for call-site compatibility
    return bool(settings.get("global_enabled", True))


def _normalize_room(room: dict, my_id: str, profiles: dict) -> dict:
    """Add other_user field to a room row for the frontend."""
    other_id = (
        room["participant_b_id"]
        if room["participant_a_id"] == my_id
        else room["participant_a_id"]
    )
    other = profiles.get(other_id, {})
    return {
        **room,
        "other_user": {
            "id": other_id,
            "username": other.get("username") or "User",
            "role": other.get("role") or "student",
            "avatar": other.get("avatar") or None,
        },
    }


def _determine_room_type(role_a: str, role_b: str) -> str:
    roles = {role_a.lower(), role_b.lower()}
    if "teacher" in roles and "student" in roles:
        return "teacher_student"
    if "teacher" in roles and "parent" in roles:
        return "parent_teacher"
    if "admin" in roles:
        return "admin_user"
    return "teacher_student"


# ── Models ────────────────────────────────────────────────────────────────────

class CreateRoomRequest(BaseModel):
    other_user_id: str


class SendMessageRequest(BaseModel):
    content: Optional[str] = None
    message_type: str = "text"         # text | image | voice | file
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_size: Optional[int] = None
    attachment_mime: Optional[str] = None


class UploadRequest(BaseModel):
    room_id: str
    file_name: str
    content_type: str
    file_size: int                     # bytes


class AdminChatSettingsRequest(BaseModel):
    global_enabled: bool = True
    allow_files: bool = True
    allow_voice: bool = True
    max_file_size_mb: int = 10
    retention_days: int = 90


# ── Student/User endpoints ────────────────────────────────────────────────────

@router.get("/api/chat/settings")
def get_my_chat_settings(user=Depends(get_current_user)):
    """Check if the current user can use platform chat."""
    profile = get_user_profile(user.id) or {}
    settings = _load_chat_settings()
    can_chat = _user_can_chat(user.id, profile, settings)
    return {
        "success": True,
        "can_use_chat": can_chat,
        "allow_files": settings.get("allow_files", True) if can_chat else False,
        "allow_voice": settings.get("allow_voice", True) if can_chat else False,
        "max_file_size_mb": settings.get("max_file_size_mb", 10),
        "global_enabled": settings.get("global_enabled", True),
    }


@router.get("/api/chat/contacts")
def list_contacts(user=Depends(get_current_user)):
    """
    Return users the current user is allowed to start a chat with.

    - Student → their assigned teacher(s) + their parent
    - Teacher → all their assigned students
    - Parent  → teachers assigned to their children
    - Admin   → all active users
    """
    profile = get_user_profile(user.id) or {}
    settings = _load_chat_settings()

    if not _user_can_chat(user.id, profile, settings):
        raise HTTPException(403, "Chat access not enabled for your account.")

    role = (profile.get("role") or "student").lower()
    contacts = []
    seen = set()

    def add_profile(p: dict):
        if p and p.get("id") and p["id"] not in seen:
            seen.add(p["id"])
            contacts.append({
                "id": p["id"],
                "username": p.get("username") or "User",
                "role": p.get("role") or "student",
                "grade": p.get("grade"),
                "avatar": p.get("avatar"),
            })

    try:
        if role == "student":
            # Assigned teachers
            asgn = (
                admin_client.table("teacher_student_assignments")
                .select("teacher_id")
                .eq("student_id", user.id)
                .execute()
            )
            teacher_ids = list({a["teacher_id"] for a in (asgn.data or []) if a.get("teacher_id")})
            if teacher_ids:
                tp = admin_client.table("profiles").select("id,username,role,grade,avatar").in_("id", teacher_ids).execute()
                for p in (tp.data or []):
                    add_profile(p)
            # Parent
            parent_id = profile.get("parent_id")
            if parent_id:
                pp = admin_client.table("profiles").select("id,username,role,grade,avatar").eq("id", parent_id).limit(1).execute()
                for p in (pp.data or []):
                    add_profile(p)

        elif role == "teacher":
            # Assigned students
            asgn = (
                admin_client.table("teacher_student_assignments")
                .select("student_id")
                .eq("teacher_id", user.id)
                .execute()
            )
            student_ids = list({a["student_id"] for a in (asgn.data or []) if a.get("student_id")})
            if student_ids:
                sp = admin_client.table("profiles").select("id,username,role,grade,avatar").in_("id", student_ids).execute()
                for p in (sp.data or []):
                    add_profile(p)

        elif role == "parent":
            # Find children
            children = (
                admin_client.table("profiles")
                .select("id,parent_id")
                .eq("parent_id", user.id)
                .execute()
            )
            child_ids = [c["id"] for c in (children.data or [])]
            # Find teachers assigned to those children
            if child_ids:
                asgn = (
                    admin_client.table("teacher_student_assignments")
                    .select("teacher_id")
                    .in_("student_id", child_ids)
                    .execute()
                )
                teacher_ids = list({a["teacher_id"] for a in (asgn.data or []) if a.get("teacher_id")})
                if teacher_ids:
                    tp = admin_client.table("profiles").select("id,username,role,grade,avatar").in_("id", teacher_ids).execute()
                    for p in (tp.data or []):
                        add_profile(p)

        elif role == "admin":
            # All active non-admin users (limited to 100 for performance)
            all_users = (
                admin_client.table("profiles")
                .select("id,username,role,grade,avatar")
                .neq("role", "admin")
                .eq("account_status", "active")
                .limit(100)
                .execute()
            )
            for p in (all_users.data or []):
                add_profile(p)

    except Exception as exc:
        return {"success": True, "contacts": [], "error": str(exc)[:200]}

    return {"success": True, "contacts": contacts}


@router.get("/api/chat/rooms")
def list_rooms(user=Depends(get_current_user)):
    """Return all chat rooms the current user participates in."""
    profile = get_user_profile(user.id) or {}
    settings = _load_chat_settings()
    if not _user_can_chat(user.id, profile, settings):
        return {"success": True, "rooms": []}

    try:
        # Get rooms where user is participant A or B
        rooms_a = (
            admin_client.table("chat_rooms")
            .select("*")
            .eq("participant_a_id", user.id)
            .eq("is_active", True)
            .order("last_message_at", desc=True)
            .execute()
        )
        rooms_b = (
            admin_client.table("chat_rooms")
            .select("*")
            .eq("participant_b_id", user.id)
            .eq("is_active", True)
            .order("last_message_at", desc=True)
            .execute()
        )

        all_rooms = (rooms_a.data or []) + (rooms_b.data or [])
        # deduplicate
        seen_ids: set = set()
        rooms = []
        for r in all_rooms:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                rooms.append(r)

        if not rooms:
            return {"success": True, "rooms": []}

        # Load other participants' profiles in batch
        other_ids = []
        for r in rooms:
            other_id = r["participant_b_id"] if r["participant_a_id"] == user.id else r["participant_a_id"]
            other_ids.append(other_id)

        profiles_resp = (
            admin_client.table("profiles")
            .select("id,username,role,grade,avatar")
            .in_("id", list(set(other_ids)))
            .execute()
        )
        profiles = {p["id"]: p for p in (profiles_resp.data or [])}

        # Get last message + unread count per room
        room_ids = [r["id"] for r in rooms]
        last_messages: dict = {}
        unread_counts: dict = {}
        for rid in room_ids:
            msgs = (
                admin_client.table("chat_messages")
                .select("id,content,message_type,sender_id,created_at,read_at,deleted_at")
                .eq("room_id", rid)
                .is_("deleted_at", "null")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if msgs.data:
                last_messages[rid] = msgs.data[0]

            unread = (
                admin_client.table("chat_messages")
                .select("id", count="exact")
                .eq("room_id", rid)
                .neq("sender_id", user.id)
                .is_("read_at", "null")
                .is_("deleted_at", "null")
                .execute()
            )
            unread_counts[rid] = unread.count or 0

        enriched = []
        for r in sorted(rooms, key=lambda x: x["last_message_at"], reverse=True):
            room_data = _normalize_room(r, user.id, profiles)
            room_data["last_message"] = last_messages.get(r["id"])
            room_data["unread_count"] = unread_counts.get(r["id"], 0)
            enriched.append(room_data)

        return {"success": True, "rooms": enriched}

    except Exception as exc:
        return {"success": True, "rooms": [], "error": str(exc)[:200]}


@router.post("/api/chat/rooms")
def get_or_create_room(body: CreateRoomRequest, user=Depends(get_current_user)):
    """Get an existing room or create one between the current user and another user."""
    profile = get_user_profile(user.id) or {}
    settings = _load_chat_settings()
    if not _user_can_chat(user.id, profile, settings):
        raise HTTPException(403, "Chat access not enabled for your account.")

    other_id = body.other_user_id
    if other_id == user.id:
        raise HTTPException(400, "Cannot create a chat room with yourself.")

    other_profile = get_user_profile(other_id)
    if not other_profile:
        raise HTTPException(404, "User not found.")

    # Canonical ordering: smaller UUID = participant_a
    a_id, b_id = sorted([user.id, other_id])

    try:
        existing = (
            admin_client.table("chat_rooms")
            .select("*")
            .eq("participant_a_id", a_id)
            .eq("participant_b_id", b_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            room = existing.data[0]
        else:
            room_type = _determine_room_type(
                profile.get("role", "student"),
                other_profile.get("role", "student"),
            )
            new_room = admin_client.table("chat_rooms").insert({
                "participant_a_id": a_id,
                "participant_b_id": b_id,
                "room_type": room_type,
            }).execute()
            room = new_room.data[0]

        profiles = {other_id: other_profile}
        return {"success": True, "room": _normalize_room(room, user.id, profiles)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Could not create room: {str(exc)[:200]}")


@router.get("/api/chat/rooms/{room_id}/messages")
def get_messages(
    room_id: str,
    limit: int = Query(50, le=100),
    before: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    """Return messages for a room (newest first, paginated by `before` timestamp)."""
    # Verify user is a participant
    try:
        room_check = (
            admin_client.table("chat_rooms")
            .select("id,participant_a_id,participant_b_id")
            .eq("id", room_id)
            .limit(1)
            .execute()
        )
    except Exception:
        raise HTTPException(404, "Room not found.")

    if not room_check.data:
        raise HTTPException(404, "Room not found.")
    room = room_check.data[0]
    if user.id not in (room["participant_a_id"], room["participant_b_id"]):
        raise HTTPException(403, "Access denied.")

    try:
        q = (
            admin_client.table("chat_messages")
            .select("*")
            .eq("room_id", room_id)
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if before:
            q = q.lt("created_at", before)
        msgs = q.execute()
        return {"success": True, "messages": list(reversed(msgs.data or []))}
    except Exception as exc:
        raise HTTPException(500, str(exc)[:200])


@router.post("/api/chat/rooms/{room_id}/messages")
def send_message(room_id: str, body: SendMessageRequest, user=Depends(get_current_user)):
    """Send a message to a chat room."""
    # Verify participant
    room_check = (
        admin_client.table("chat_rooms")
        .select("id,participant_a_id,participant_b_id,is_active")
        .eq("id", room_id)
        .limit(1)
        .execute()
    )
    if not room_check.data:
        raise HTTPException(404, "Room not found.")
    room = room_check.data[0]
    if user.id not in (room["participant_a_id"], room["participant_b_id"]):
        raise HTTPException(403, "Access denied.")
    if not room["is_active"]:
        raise HTTPException(403, "This conversation has been deactivated by an admin.")

    settings = _load_chat_settings()
    profile = get_user_profile(user.id) or {}
    if not _user_can_chat(user.id, profile, settings):
        raise HTTPException(403, "Chat access not enabled.")

    if not body.content and not body.attachment_url:
        raise HTTPException(400, "Message must have content or an attachment.")

    msg_type = body.message_type
    if msg_type in ("image", "voice", "file") and not settings.get("allow_files", True):
        raise HTTPException(403, "File sharing is disabled by the admin.")

    # File size check
    if body.attachment_size and body.attachment_size > settings.get("max_file_size_mb", 10) * 1024 * 1024:
        raise HTTPException(413, f"File exceeds maximum size of {settings.get('max_file_size_mb', 10)} MB.")

    from datetime import timedelta  # noqa: PLC0415
    retention_days = settings.get("retention_days", 90)
    expires_at = None
    if retention_days and retention_days > 0:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=retention_days)).isoformat()

    row = {
        "room_id": room_id,
        "sender_id": user.id,
        "content": (body.content or "")[:4000] or None,
        "message_type": msg_type,
        "attachment_url": body.attachment_url,
        "attachment_name": body.attachment_name,
        "attachment_size": body.attachment_size,
        "attachment_mime": body.attachment_mime,
        "expires_at": expires_at,
    }

    try:
        result = admin_client.table("chat_messages").insert(row).execute()
        # Update room's last_message_at
        admin_client.table("chat_rooms").update(
            {"last_message_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", room_id).execute()
        return {"success": True, "message": result.data[0] if result.data else row}
    except Exception as exc:
        raise HTTPException(500, f"Failed to send message: {str(exc)[:200]}")


@router.post("/api/chat/rooms/{room_id}/read")
def mark_room_read(room_id: str, user=Depends(get_current_user)):
    """Mark all unread messages from the other user as read."""
    try:
        admin_client.table("chat_messages").update(
            {"read_at": datetime.now(timezone.utc).isoformat()}
        ).eq("room_id", room_id).neq("sender_id", user.id).is_("read_at", "null").execute()
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)[:200]}


@router.post("/api/chat/upload")
def get_upload_url(body: UploadRequest, user=Depends(get_current_user)):
    """
    Return a signed Supabase Storage upload URL for a chat attachment.
    The client uploads directly to Supabase Storage, then sends the resulting
    public URL as attachment_url in the send-message request.
    """
    settings = _load_chat_settings()
    if not settings.get("allow_files", True):
        raise HTTPException(403, "File sharing is disabled.")

    max_bytes = settings.get("max_file_size_mb", 10) * 1024 * 1024
    if body.file_size > max_bytes:
        raise HTTPException(413, f"File exceeds {settings.get('max_file_size_mb', 10)} MB limit.")

    profile = get_user_profile(user.id) or {}
    if not _user_can_chat(user.id, profile, settings):
        raise HTTPException(403, "Chat access not enabled.")

    import re  # noqa: PLC0415
    safe_name = re.sub(r"[^\w.\-]", "_", body.file_name)[:100]
    storage_path = f"{body.room_id}/{user.id}_{safe_name}"

    try:
        result = admin_client.storage.from_("chat-attachments").create_signed_upload_url(storage_path)
        return {
            "success": True,
            "upload_url": result.get("signedUrl") or result.get("signed_url"),
            "path": storage_path,
            "token": result.get("token"),
        }
    except Exception as exc:
        raise HTTPException(500, f"Could not create upload URL: {str(exc)[:200]}")


@router.delete("/api/chat/messages/{msg_id}")
def delete_message(msg_id: str, user=Depends(get_current_user)):
    """Soft-delete a message (only the sender can delete their own messages)."""
    try:
        existing = admin_client.table("chat_messages").select("id,sender_id").eq("id", msg_id).limit(1).execute()
        if not existing.data:
            raise HTTPException(404, "Message not found.")
        if existing.data[0]["sender_id"] != user.id:
            raise HTTPException(403, "You can only delete your own messages.")
        admin_client.table("chat_messages").update(
            {"deleted_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", msg_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)[:200])


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.get("/api/admin/chat/settings")
def admin_get_chat_settings(admin_user=Depends(require_admin)):
    return {"success": True, **_load_chat_settings()}


@router.put("/api/admin/chat/settings")
def admin_update_chat_settings(body: AdminChatSettingsRequest, admin_user=Depends(require_admin)):
    value = {
        "global_enabled": body.global_enabled,
        "allow_files": body.allow_files,
        "allow_voice": body.allow_voice,
        "max_file_size_mb": max(1, min(50, body.max_file_size_mb)),
        "retention_days": max(0, body.retention_days),
    }
    try:
        admin_client.table("admin_settings").upsert(
            {"key": CHAT_SETTINGS_KEY, "value": value, "updated_at": "now()"},
            on_conflict="key",
        ).execute()
    except Exception as exc:
        raise HTTPException(500, f"Could not save chat settings: {str(exc)[:200]}")
    return {"success": True, **value, "message": "Chat settings saved."}


@router.get("/api/admin/chat/users")
def admin_list_chat_users(admin_user=Depends(require_admin)):
    """List users with explicit chat access grants."""
    ids = _get_chat_user_ids()
    if not ids:
        return {"success": True, "users": []}
    try:
        resp = admin_client.table("profiles").select("id,username,email,role,grade,subscription_plan").in_("id", ids).execute()
        users = [{**p, "chat_access": True} for p in (resp.data or [])]
        return {"success": True, "users": users}
    except Exception as exc:
        return {"success": True, "users": [], "error": str(exc)[:100]}


@router.patch("/api/admin/chat/users/{user_id}")
def admin_toggle_chat_access(user_id: str, enabled: bool, admin_user=Depends(require_admin)):
    """Grant or revoke chat access for a specific user."""
    ids = _get_chat_user_ids()
    if enabled:
        if user_id not in ids:
            ids.append(user_id)
    else:
        ids = [uid for uid in ids if uid != user_id]
    _set_chat_user_ids(ids)
    return {"success": True, "user_id": user_id, "chat_access": enabled}


@router.get("/api/admin/chat/rooms")
def admin_list_rooms(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    admin_user=Depends(require_admin),
):
    """Admin moderation view — all chat rooms with participant info."""
    try:
        rooms = (
            admin_client.table("chat_rooms")
            .select("*")
            .order("last_message_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        if not rooms.data:
            return {"success": True, "rooms": []}

        all_ids = []
        for r in rooms.data:
            all_ids.extend([r["participant_a_id"], r["participant_b_id"]])
        profiles_resp = admin_client.table("profiles").select("id,username,role,grade").in_("id", list(set(all_ids))).execute()
        profiles = {p["id"]: p for p in (profiles_resp.data or [])}

        enriched = []
        for r in rooms.data:
            pa = profiles.get(r["participant_a_id"], {"username": "?"})
            pb = profiles.get(r["participant_b_id"], {"username": "?"})
            # Message count
            cnt = admin_client.table("chat_messages").select("id", count="exact").eq("room_id", r["id"]).is_("deleted_at", "null").execute()
            enriched.append({
                **r,
                "participant_a": pa,
                "participant_b": pb,
                "message_count": cnt.count or 0,
            })
        return {"success": True, "rooms": enriched, "total": len(enriched)}
    except Exception as exc:
        return {"success": True, "rooms": [], "error": str(exc)[:200]}


@router.delete("/api/admin/chat/rooms/{room_id}")
def admin_deactivate_room(room_id: str, admin_user=Depends(require_admin)):
    """Admin: deactivate a chat room (participants can no longer send messages)."""
    result = admin_client.table("chat_rooms").update({"is_active": False}).eq("id", room_id).execute()
    if not result.data:
        raise HTTPException(404, "Room not found.")
    try:
        admin_client.table("platform_audit_logs").insert({
            "admin_id": admin_user["auth_user"].id,
            "action": "chat_room_deactivated",
            "target_id": room_id,
            "details": json.dumps({"room_id": room_id}),
        }).execute()
    except Exception:
        pass
    return {"success": True, "room_id": room_id, "message": "Room deactivated."}
