from typing import Annotated, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from fob_api import auth, engine
from fob_api.models.database import User, HeadScalePolicyACL, HeadScalePolicyHost
from fob_api.models.api import HeadScalePolicyAcl as HeadScalePolicyAclAPI
from fob_api.models.api import HeadScalePolicyAclCreate as HeadScalePolicyAclCreateAPI
from fob_api.models.api import HeadScalePolicyHost as HeadScalePolicyHostAPI
from fob_api.models.api import HeadScalePolicyHostCreate as HeadScalePolicyHostCreateAPI
from fob_api.tasks.headscale import update_headscale_policy

router = APIRouter(prefix="/headscale")

@router.get("/acls/", tags=["vpn"])
def list(user: Annotated[User, Depends(auth.get_current_user)]) -> List[HeadScalePolicyAclAPI]:
    """
    Return list of HeadScale ACLs in Policy
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    with Session(engine) as session:
        acls = session.exec(select(HeadScalePolicyACL)).all()
    return [HeadScalePolicyAclAPI(
        id=acl.id,
        action=acl.action,
        src=acl.src.split(","),
        dst=acl.dst.split(","),
        proto=acl.proto,
    ) for acl in acls]

@router.post("/acls/", tags=["vpn"])
def create(
    acl: HeadScalePolicyAclCreateAPI,
    user: Annotated[User, Depends(auth.get_current_user)],
) -> HeadScalePolicyAclAPI | None:
    """
    Create a new HeadScale ACL in Policy
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    with Session(engine) as session:
        new_acl = HeadScalePolicyACL(**acl.model_dump())
        session.add(new_acl)
        session.commit()
        session.refresh(new_acl)

        try:
            update_headscale_policy()
        except Exception as e:
            session.delete(new_acl)
            session.commit()
            raise HTTPException(status_code=400, detail=f"Failed to apply new policy: {e}")
        return HeadScalePolicyAclAPI(
            id=new_acl.id,
            action=new_acl.action,
            src=new_acl.src.split(","),
            dst=new_acl.dst.split(","),
            proto=new_acl.proto,
        )

@router.delete("/acls/{acl_id}/", tags=["vpn"])
def delete(
    acl_id: int,
    user: Annotated[User, Depends(auth.get_current_user)],
) -> None:
    """
    Delete a HeadScale ACL from Policy
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    with Session(engine) as session:
        acl = session.get(HeadScalePolicyACL, acl_id)
        if not acl:
            raise HTTPException(status_code=404, detail="ACL not found")
        session.delete(acl)
        session.commit()
        try:
            update_headscale_policy()
        except Exception as e:
            session.add(acl)
            session.commit()
            raise HTTPException(status_code=400, detail=f"Failed to apply new policy: {e}")

@router.get("/host/", tags=["vpn"])
def list_hosts(user: Annotated[User, Depends(auth.get_current_user)]) -> List[HeadScalePolicyHostAPI]:
    """
    Return list of HeadScale hosts
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    with Session(engine) as session:
        headscale_policy_host = session.exec(select(HeadScalePolicyHost)).all()
    return headscale_policy_host

@router.post("/host/", tags=["vpn"])
def create_host(
    host: HeadScalePolicyHostCreateAPI,
    user: Annotated[User, Depends(auth.get_current_user)],
) -> HeadScalePolicyHostAPI | None:
    """
    Create a new HeadScale host
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    with Session(engine) as session:

        new_host = HeadScalePolicyHost(**host.model_dump())
        session.add(new_host)
        try:
            session.commit()
        except IntegrityError:
            raise HTTPException(status_code=400, detail="This host binding already exists")
        session.refresh(new_host)
        try:
            update_headscale_policy()
        except Exception as e:
            session.delete(new_host)
            session.commit()
            raise HTTPException(status_code=400, detail=f"Failed to apply new policy: {e}")
        return new_host

@router.delete("/host/{host_id}/", tags=["vpn"])
def delete_host(
    host_id: int,
    user: Annotated[User, Depends(auth.get_current_user)],
) -> None:
    """
    Delete a HeadScale host
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    with Session(engine) as session:
        host = session.get(HeadScalePolicyHost, host_id)
        if not host:
            raise HTTPException(status_code=404, detail="Host not found")
        session.delete(host)
        session.commit()
        try:
            update_headscale_policy()
        except Exception as e:
            session.add(host)
            session.commit()
            raise HTTPException(status_code=400, detail=f"Failed to apply new policy: {e}")
