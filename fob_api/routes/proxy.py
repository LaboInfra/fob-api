from datetime import datetime, timedelta
from typing import Annotated
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from fob_api import auth, get_session
from fob_api import Config
from fob_api.managers import ProxyManager
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fob_api.models.database import (
    ProxyServiceMap,
    ProxyServiceMapCreate,
    ProxyServiceMapPublic,
    User,
    Project
)

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

@router.post("/", tags=["proxy"], response_model=ProxyServiceMapPublic)
def create_proxy_service_map(
        service_map: ProxyServiceMapCreate,
        session: Session = Depends(get_session),
        user: User = Depends(auth.get_current_user),
    ):
    project = auth.is_project_owner_or_member(user, service_map.project_id)
    pm = ProxyManager(session)
    
    if not pm.validate_targets(service_map.target.split(",")):
        raise HTTPException(status_code=400, detail="Invalid target format")
    if service_map.rule.startswith("http://") or service_map.rule.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail="Rule must be a domain name, not a URL. Use '`example.com`' format."
        )
    return pm.create_proxy(
        project=project,
        rule=service_map.rule,
        target=service_map.target
    )

@router.get("/{project_id}", tags=["proxy"], response_model=list[ProxyServiceMapPublic])
def get_proxy_service_maps(
        project_id: int,
        session: Session = Depends(get_session),
        user: User = Depends(auth.get_current_user),
    ):
    project = auth.is_project_owner_or_member(user, project_id)
    pm = ProxyManager(session)
    return pm.get_proxy_by_project(project)

@router.delete("/{proxy_id}", tags=["proxy"])
def delete_proxy_service_map(
        proxy_id: int,
        session: Session = Depends(get_session),
        user: User = Depends(auth.get_current_user),
    ):
    pm = ProxyManager(session)
    proxy = session.get(ProxyServiceMap, proxy_id)    
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy service map not found")
    project = auth.is_project_owner_or_member(user, proxy.project_id)
    if proxy.project_id != project.id:
        raise HTTPException(status_code=403, detail="Not enough permissions to delete this proxy service map")
    return pm.delete_proxy(proxy)