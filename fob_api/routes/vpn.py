from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from fob_api import auth
from fob_api.models.database import User
from fob_api.models.api import CreateDevice
from fob_api.tasks import headscale

router = APIRouter(prefix="/devices")

@router.get("/{username}", tags=["vpn"])
def list_user_devices(user: Annotated[User, Depends(auth.get_current_user)], username: str):
    """
    List all devices for a user
    """
    if not user.is_admin and user.username != username:
        raise HTTPException(status_code=403, detail="You are not an admin")
    return None

@router.post("/{username}", tags=["vpn"])
def create_device(user: Annotated[User, Depends(auth.get_current_user)], username: str, device: CreateDevice):
    """
    Create a new device for a user
    """
    if not user.is_admin and user.username != username:
        raise HTTPException(status_code=403, detail="You are not an admin")
    return None

@router.delete("/{username}/{device_id}", tags=["vpn"])
def delete_device(user: Annotated[User, Depends(auth.get_current_user)], username: str, device_id: str):
    """
    Delete a device for a user
    """
    if not user.is_admin and user.username != username:
        raise HTTPException(status_code=403, detail="You are not an admin")
    devices = None
    for device in devices:
        if device.id == device_id:
            return None
    raise HTTPException(status_code=404, detail="Device not found")
