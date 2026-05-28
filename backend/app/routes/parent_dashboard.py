from fastapi import APIRouter, Depends

from app.services.auth_service import get_current_user
from app.services.parent_dashboard_service import get_children

router = APIRouter()


@router.get("/children")
def get_parent_children(user=Depends(get_current_user)):
    children = get_children(user.id)

    return {
        "success": True,
        "children": children
    }