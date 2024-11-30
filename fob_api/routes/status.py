from typing import Annotated

from fastapi import APIRouter, Depends

from fob_api import auth
from fob_api.models.database.user import User
from fob_api.models.api import Me
from fob_api.tasks import firezone

router = APIRouter()



@router.get("/me", tags=["users"], response_model=Me)
def me(user: Annotated[User, Depends(auth.get_current_user)]) -> Me:
    """
    Returns global Me information.
    TODO: Add list of projects
    TODO: add status of quotas
    """
    devices_access = [item.__dict__ for item in firezone.get_devices_for_user(user.username)]
    return Me(
        username=user.username,
        email=user.email,
        devices_access=devices_access
    )
