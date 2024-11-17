from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session, select
from celery.result import AsyncResult
from firezone_client import generate_password

from fob_api import auth, engine, TaskInfo
from fob_api.models.user import User
from fob_api.tasks.core import sync_user as task_sync_user
from fob_api.tasks import firezone
from fob_api.auth import hash_password
from fob_api.worker import celery

router = APIRouter(prefix="/devices")

class CreateDevice(BaseModel):
    name: str

@router.get("/{username}", tags=["vpn"])
def list_user_devices(user: Annotated[User, Depends(auth.get_current_user)], username: str):
    """
    List all devices for a user
    """
    if not user.is_admin and user.username != username:
        raise HTTPException(status_code=403, detail="You are not an admin")
    devices = firezone.get_devices_for_user(username)
    return devices

@router.post("/{username}", tags=["vpn"])
def create_device(user: Annotated[User, Depends(auth.get_current_user)], username: str, device: CreateDevice):
    """
    Create a new device for a user
    """
    if not user.is_admin and user.username != username:
        raise HTTPException(status_code=403, detail="You are not an admin")
    return firezone.create_device(username, device.name)

@router.delete("/{username}/{device_id}", tags=["vpn"])
def delete_device(user: Annotated[User, Depends(auth.get_current_user)], username: str, device_id: str):
    """
    Delete a device for a user
    """
    if not user.is_admin and user.username != username:
        raise HTTPException(status_code=403, detail="You are not an admin")
    return firezone.delete_device(device_id)
