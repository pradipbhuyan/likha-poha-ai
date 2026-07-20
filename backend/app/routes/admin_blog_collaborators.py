"""
admin_blog_collaborators.py  —  /api/admin-control/*
─────────────────────────────────────────────────────────────────────────────
GitHub repository collaborator management for blog editor access.

Extracted from app/routes/admin_control.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import require_admin

router = APIRouter()


class AddBlogCollaboratorRequest(BaseModel):
    github_username: str
    permission: str = "push"   # "push" = write access to edit .md files


@router.get("/blog-collaborators")
def list_blog_collaborators(admin=Depends(require_admin)):
    """List current GitHub repository collaborators."""
    import os as _os  # noqa: PLC0415
    import requests as _req  # noqa: PLC0415

    token = _os.getenv("GITHUB_TOKEN", "")
    repo = _os.getenv("GITHUB_REPO", "pradipbhuyan/likha-poha-ai")

    if not token:
        return {"success": False, "error": "GITHUB_TOKEN not set in backend .env", "collaborators": []}

    try:
        r = _req.get(
            f"https://api.github.com/repos/{repo}/collaborators",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if not r.ok:
            return {"success": False, "error": f"GitHub API error: {r.status_code} — {r.text[:200]}", "collaborators": []}
        data = r.json()
        return {
            "success": True,
            "collaborators": [
                {
                    "username": c.get("login"),
                    "avatar": c.get("avatar_url"),
                    "permission": c.get("role_name") or c.get("permissions", {}),
                    "profile_url": c.get("html_url"),
                }
                for c in data
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e), "collaborators": []}


@router.post("/blog-collaborators")
def add_blog_collaborator(data: AddBlogCollaboratorRequest, admin=Depends(require_admin)):
    """Invite a GitHub user as a repository collaborator (blog editor access)."""
    import os as _os  # noqa: PLC0415
    import requests as _req  # noqa: PLC0415

    token = _os.getenv("GITHUB_TOKEN", "")
    repo = _os.getenv("GITHUB_REPO", "pradipbhuyan/likha-poha-ai")

    if not token:
        raise HTTPException(
            status_code=503,
            detail="GITHUB_TOKEN not configured in backend .env. Add it to enable blog collaborator management.",
        )

    username = data.github_username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="GitHub username is required.")

    valid_permissions = {"pull", "push", "admin", "maintain", "triage"}
    permission = data.permission if data.permission in valid_permissions else "push"

    try:
        r = _req.put(
            f"https://api.github.com/repos/{repo}/collaborators/{username}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"permission": permission},
            timeout=10,
        )
        if r.status_code == 201:
            return {"success": True, "message": f"Invitation sent to @{username}. They will receive an email to accept.", "status": "invited"}
        elif r.status_code == 204:
            return {"success": True, "message": f"@{username} is already a collaborator.", "status": "already_collaborator"}
        elif r.status_code == 404:
            raise HTTPException(status_code=404, detail=f"GitHub user '{username}' not found.")
        else:
            raise HTTPException(status_code=r.status_code, detail=f"GitHub API error: {r.text[:300]}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/blog-collaborators/{github_username}")
def remove_blog_collaborator(github_username: str, admin=Depends(require_admin)):
    """Remove a GitHub repository collaborator."""
    import os as _os  # noqa: PLC0415
    import requests as _req  # noqa: PLC0415

    token = _os.getenv("GITHUB_TOKEN", "")
    repo = _os.getenv("GITHUB_REPO", "pradipbhuyan/likha-poha-ai")

    if not token:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN not configured.")

    try:
        r = _req.delete(
            f"https://api.github.com/repos/{repo}/collaborators/{github_username}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if r.status_code in (204, 404):
            return {"success": True, "message": f"@{github_username} removed from collaborators."}
        raise HTTPException(status_code=r.status_code, detail=f"GitHub API error: {r.text[:200]}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
