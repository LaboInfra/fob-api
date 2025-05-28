from datetime import datetime, timedelta
from typing import Annotated
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from fob_api import auth, get_session
from fob_api import Config
from fob_api.managers import ProxyManager
from fastapi.security import HTTPBasic, HTTPBasicCredentials

router = APIRouter(prefix="/proxy")

security = HTTPBasic()

@router.get("/", tags=["proxy"])
def get_users(
        credentials: Annotated[HTTPBasicCredentials, Depends(security)],
        session: Session = Depends(get_session)
    ):
    if not (secrets.compare_digest(credentials.username, "traefik") and 
            secrets.compare_digest(credentials.password, Config().traefik_config_password)):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"}
        )
    pm = ProxyManager(session)
    return pm.build_treafik_config()