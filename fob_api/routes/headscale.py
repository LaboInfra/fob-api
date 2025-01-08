from typing import Annotated, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from fob_api import auth, engine
from fob_api.models.database import User, HeadScalePolicyACL
from fob_api.models.api import HeadScalePolicyAcl as HeadScalePolicyAclAPI
from fob_api.models.api import HeadScalePolicyAclCreate as HeadScalePolicyAclCreateAPI
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
    return acls

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
