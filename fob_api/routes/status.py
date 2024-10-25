from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from fob_api import auth
from fob_api.models.user import User

router = APIRouter()

class Status(BaseModel):
    username: str
    email: str


@router.get("/status/", tags=["status"], response_model=Status)
def status(user: Annotated[User, Depends(auth.get_current_user)]) -> Status:
    """
    Returns global status information.
    TODO: Add Total vpn devices registered
    TODO: Add list of projects
    TODO: add status of quotas
    """
    return Status(username=user.username, email=user.email)
