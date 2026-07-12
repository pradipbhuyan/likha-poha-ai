/**
 * platformChat.js — API client for user-to-user platform chat
 */
import { authFetch } from "./authClient";
import { supabase } from "./supabaseClient";

const BUCKET = "chat-attachments";

// ── Chat settings ─────────────────────────────────────────────────────────────
export async function getChatSettings() {
  return authFetch("/api/chat/settings");
}

// ── Contacts ──────────────────────────────────────────────────────────────────
export async function getChatContacts() {
  return authFetch("/api/chat/contacts");
}

// ── Rooms ─────────────────────────────────────────────────────────────────────
export async function getChatRooms() {
  return authFetch("/api/chat/rooms");
}

export async function getOrCreateRoom(otherUserId) {
  return authFetch("/api/chat/rooms", {
    method: "POST",
    body: JSON.stringify({ other_user_id: otherUserId }),
  });
}

// ── Messages ──────────────────────────────────────────────────────────────────
export async function getRoomMessages(roomId, { limit = 50, before } = {}) {
  const params = new URLSearchParams({ limit });
  if (before) params.append("before", before);
  return authFetch(`/api/chat/rooms/${roomId}/messages?${params}`);
}

export async function sendMessage(roomId, payload) {
  return authFetch(`/api/chat/rooms/${roomId}/messages`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function markRoomRead(roomId) {
  return authFetch(`/api/chat/rooms/${roomId}/read`, { method: "POST" });
}

export async function deleteMessage(msgId) {
  return authFetch(`/api/chat/messages/${msgId}`, { method: "DELETE" });
}

// ── File uploads ──────────────────────────────────────────────────────────────

/**
 * Compress an image File to JPEG at the given quality (0–1).
 * Returns a new Blob. Falls back to original file on canvas error.
 */
async function compressImage(file, quality = 0.8) {
  return new Promise((resolve) => {
    try {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        URL.revokeObjectURL(url);
        const canvas = document.createElement("canvas");
        const MAX = 1920;
        let { width, height } = img;
        if (width > MAX) { height = Math.round((height * MAX) / width); width = MAX; }
        if (height > MAX) { width = Math.round((width * MAX) / height); height = MAX; }
        canvas.width = width;
        canvas.height = height;
        canvas.getContext("2d").drawImage(img, 0, 0, width, height);
        canvas.toBlob((blob) => resolve(blob || file), "image/jpeg", quality);
      };
      img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
      img.src = url;
    } catch {
      resolve(file);
    }
  });
}

/**
 * Upload a file attachment directly via the Supabase JS client.
 * Requires Storage policies: INSERT + SELECT for authenticated users on chat-attachments.
 * Returns { url, name, size, mime } on success.
 */
export async function uploadChatFile(roomId, file) {
  let uploadFile = file;

  // Compress images larger than 2 MB
  if (file.type.startsWith("image/") && file.size > 2 * 1024 * 1024) {
    uploadFile = await compressImage(file, 0.8);
  }

  // Get current user ID for path namespacing
  const { data: { user }, error: authErr } = await supabase.auth.getUser();
  if (authErr || !user) throw new Error("Not authenticated");

  const safeName = file.name.replace(/[^\w.\-]/g, "_").slice(0, 100);
  const storagePath = `${roomId}/${user.id}_${Date.now()}_${safeName}`;

  // Upload directly via Supabase JS (uses user's JWT — bypasses need for signed upload URLs)
  const { data: uploadData, error: uploadErr } = await supabase.storage
    .from(BUCKET)
    .upload(storagePath, uploadFile, {
      contentType: uploadFile.type || "application/octet-stream",
      upsert: false,
    });

  if (uploadErr) throw new Error(uploadErr.message);

  // Get a signed download URL (1 hour expiry)
  const { data: signedData, error: signErr } = await supabase.storage
    .from(BUCKET)
    .createSignedUrl(uploadData.path, 3600);

  if (signErr) throw new Error(signErr.message);

  return {
    url: signedData.signedUrl,
    name: file.name,
    size: uploadFile.size,
    mime: uploadFile.type || "application/octet-stream",
  };
}

// ── Supabase Realtime subscription ────────────────────────────────────────────

/**
 * Subscribe to new messages in a room via Supabase Realtime.
 * Returns an unsubscribe function.
 */
export function subscribeToRoom(roomId, onMessage) {
  const channel = supabase
    .channel(`chat:${roomId}`)
    .on(
      "postgres_changes",
      {
        event: "INSERT",
        schema: "public",
        table: "chat_messages",
        filter: `room_id=eq.${roomId}`,
      },
      (payload) => {
        if (payload.new && !payload.new.deleted_at) {
          onMessage(payload.new);
        }
      }
    )
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
}

// ── Admin ──────────────────────────────────────────────────────────────────────
export async function adminGetChatSettings() {
  return authFetch("/api/admin/chat/settings");
}

export async function adminSaveChatSettings(settings) {
  return authFetch("/api/admin/chat/settings", {
    method: "PUT",
    body: JSON.stringify(settings),
  });
}

export async function adminListChatUsers() {
  return authFetch("/api/admin/chat/users");
}

export async function adminToggleChatAccess(userId, enabled) {
  return authFetch(`/api/admin/chat/users/${userId}?enabled=${enabled}`, {
    method: "PATCH",
  });
}

export async function adminListChatRooms() {
  return authFetch("/api/admin/chat/rooms");
}

export async function adminDeactivateChatRoom(roomId) {
  return authFetch(`/api/admin/chat/rooms/${roomId}`, { method: "DELETE" });
}
