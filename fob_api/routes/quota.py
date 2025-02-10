from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from fob_api import auth, engine, openstack, get_session
from fob_api.models import database as db_models
from fob_api.models import api as api_models

#
# This is the most awful code I've ever written sorry for the future reader
# 10/02 the code has been refactored but still need a lot of work
#

router = APIRouter(prefix="/quota")

#--------------------------------
# TODO: move to tasks
def calculate_user_quota_by_type(user: db_models.User, quota_type: db_models.QuotaType) -> api_models.AdjustUserQuota:
    with Session(engine) as session:
        calculated_quota = 0
        for q in session.exec(select(db_models.UserQuota).where(db_models.UserQuota.user_id == user.id).where(db_models.UserQuota.type == quota_type)).all():
            calculated_quota += q.quantity
        return api_models.AdjustUserQuota(
            username=user.username,
            type=quota_type,
            quantity=calculated_quota,
            comment="Calculated total quota for user"
        )

def calculate_user_quota(user: db_models.User) -> List[api_models.AdjustUserQuota]:
    with Session(engine) as session:
        user_max_quota_dict = {k: 0 for k in db_models.QuotaType}
        for q in session.exec(select(db_models.UserQuota).where(db_models.UserQuota.user_id == user.id)).all():
            user_max_quota_dict[db_models.QuotaType.from_str(q.type)] += q.quantity
        
        return [api_models.AdjustUserQuota(
            username=user.username,
            type=k,
            quantity=v,
            comment="Calculated total all type quota for user"
        ) for k, v in user_max_quota_dict.items()]

def calculate_project_quota(project: db_models.Project) -> List[api_models.AdjustProjectQuota]:
    with Session(engine) as session:
        project_max_quota_dict = {k: 0 for k in db_models.QuotaType}
        for q in session.exec(select(db_models.UserQuotaShare).where(db_models.UserQuotaShare.project_id == project.id)).all():
            project_max_quota_dict[db_models.QuotaType.from_str(q.type)] += q.quantity
        
        return [api_models.AdjustProjectQuota(
            username="",
            project_name=project.name,
            type=k,
            quantity=v,
            comment="Calculated total all type quota for project"
        ) for k, v in project_max_quota_dict.items()]

def sync_project_quota(openstack_project: db_models.Project) -> None:
    nova_client = openstack.get_nova_client()
    cinder_client = openstack.get_cinder_client()
    keystone_client = openstack.get_keystone_client()

    project_id = keystone_client.projects.find(name=openstack_project.name).id

    for quota in calculate_project_quota(openstack_project):
        print(f"Syncing quota for project: {openstack_project.name} with type: {quota.type} and quantity: {quota.quantity}")
        match quota.type:
            case db_models.QuotaType.CPU:
                nova_client.quotas.update(tenant_id=project_id, cores=quota.quantity)
            case db_models.QuotaType.MEMORY:
                nova_client.quotas.update(tenant_id=project_id, ram=quota.quantity)
            case db_models.QuotaType.STORAGE:
                cinder_client.quotas.update(tenant_id=project_id, gigabytes=quota.quantity)
            case _:
                print(f"Unknown quota type: {quota.type} for project: {openstack_project.name} with quantity: {quota.quantity}")

def get_user_left_quota_by_type(user: db_models.User, quota_type: db_models.QuotaType) -> int:
    with Session(engine) as session:
        user_quota_own = 0
        for q in session.exec(select(db_models.UserQuota).where(db_models.UserQuota.user_id == user.id).where(db_models.UserQuota.type == quota_type)).all():
            user_quota_own += q.quantity
        
        user_quota_used = 0
        for q in session.exec(select(db_models.UserQuotaShare).where(db_models.UserQuotaShare.user_id == user.id).where(db_models.UserQuotaShare.type == quota_type)).all():
            user_quota_used += q.quantity

        return user_quota_own - user_quota_used

#--------------------------------

@router.post("/adjust-user", tags=["quota"])
def give_quota_to_user(
        create_quota: api_models.AdjustUserQuota,
        user: Annotated[db_models.User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> api_models.AdjustUserQuota:
    """Give quota to a user"""
    auth.is_admin(user)
    user_find = session.exec(select(db_models.User).where(db_models.User.username == create_quota.username)).first()
    if not user_find:
        raise HTTPException(status_code=400, detail="User not found")
    if create_quota.quantity == 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be 0")
    new_quota = db_models.UserQuota(
        user_id=user_find.id,
        comment=create_quota.comment,
        quantity=create_quota.quantity,
        type=create_quota.type
    )
    session.add(new_quota)
    session.commit()
    return calculate_user_quota_by_type(user_find, create_quota.type)

@router.delete("/adjust-user/{id}", tags=["quota"])
def remove_quota_attribution_for_user(
        id: int,
        user: Annotated[db_models.User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> api_models.AdjustUserQuota:
    """Remove quota attribution for a user"""
    auth.is_admin(user)
    quota = session.exec(select(db_models.UserQuota).where(db_models.UserQuota.id == id)).first()
    if not quota:
        raise HTTPException(status_code=400, detail="Adjustement not found")
    session.delete(quota)
    session.commit()
    return calculate_user_quota_by_type(user, quota.type)

@router.get("/user/{username}/total", tags=["quota"])
def show_user_quota(
        username: str,
        user: Annotated[db_models.User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> List[api_models.AdjustUserQuota]:
    """Show total adjustements for a user grouped by type"""
    auth.is_admin_or_self(user, username)
    user_find = session.exec(select(db_models.User).where(db_models.User.username == username)).first()
    if not user_find:
        raise HTTPException(status_code=400, detail="User not found")
    return calculate_user_quota(user_find)

@router.get("/user/{username}/adjustements", tags=["quota"])
def show_user_adjustements(
        username: str,
        user: Annotated[db_models.User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> List[api_models.AdjustUserQuotaID]:
    """Show all adjustements for a user"""
    auth.is_admin_or_self(user, username)
    user_find = session.exec(select(db_models.User).where(db_models.User.username == username)).first()
    if not user_find:
        raise HTTPException(status_code=400, detail="User not found")
    return [api_models.AdjustUserQuotaID(
        id=q.id,
        username=user_find.username,
        type=db_models.QuotaType.from_str(q.type),
        quantity=q.quantity,
        comment=q.comment
    ) for q in session.exec(select(db_models.UserQuota).where(db_models.UserQuota.user_id == user_find.id)).all()]

@router.post("/adjust-project", tags=["quota"])
def share_quota_to_project(
        create_quota: api_models.AdjustProjectQuota,
        user: Annotated[db_models.User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> List[api_models.AdjustProjectQuota]:
    """Share quota to a project"""
    auth.is_admin_or_self(user, create_quota.username)

    user_find = session.exec(select(db_models.User).where(db_models.User.username == create_quota.username)).first()
    if not user_find:
        raise HTTPException(status_code=400, detail="User not found")
    project_find = session.exec(select(db_models.Project).where(db_models.Project.name == create_quota.project_name)).first()
    if not project_find:
        raise HTTPException(status_code=400, detail="Project not found")
    project_membership = session.exec(select(db_models.ProjectUserMembership).where(db_models.ProjectUserMembership.project_id == project_find.id, db_models.ProjectUserMembership.user_id == user_find.id)).first()
    if not project_membership and project_find.owner_id != user_find.id:
        raise HTTPException(status_code=400, detail="User not in project")
    if create_quota.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity cannot be less than 1 if you want to remove quota use the delete endpoint")
    
    if get_user_left_quota_by_type(user_find, db_models.QuotaType.from_str(create_quota.type)) < create_quota.quantity:
        raise HTTPException(status_code=400, detail="User do not have enough quota to share")

    new_quota = db_models.UserQuotaShare(
        user_id=user_find.id,
        project_id=project_find.id,
        comment=create_quota.comment,
        quantity=create_quota.quantity,
        type=create_quota.type
    )

    session.add(new_quota)
    session.commit()
    
    sync_project_quota(project_find)
    return calculate_project_quota(project_find)

# can take back quota from projects
@router.delete("/adjust-project/{id}/{username}", tags=["quota"])
def remove_quota_attribution_for_project(
        id: int,
        username: str,
        user: Annotated[db_models.User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> List[api_models.AdjustProjectQuota]:
    """Remove quota attribution for a project"""
    auth.is_admin_or_self(user, username)
    quota = session.exec(select(db_models.UserQuotaShare).where(db_models.UserQuotaShare.id == id).where(db_models.UserQuotaShare.user_id == user.id)).first()
    if not quota:
        raise HTTPException(status_code=400, detail="Project adjustement not found")
    project = session.exec(select(db_models.Project).where(db_models.Project.id == quota.project_id)).first()
    session.delete(quota)
    session.commit()
    try:
        sync_project_quota(project)
    except Exception as e:
        print(e)
        # this is when quota try to be removed but project use the quota
        # todo if needed to rebuild quota object
        session.add(quota)
        session.commit()
        sync_project_quota(project)
    return calculate_project_quota(project)

@router.get("/project/{project_name}/total", tags=["quota"])
def show_project_quota(
        project_name: str,
        user: Annotated[db_models.User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> List[api_models.AdjustProjectQuota]:
    """Show total adjustements for a project grouped by type"""
    project_find = session.exec(select(db_models.Project).where(db_models.Project.name == project_name)).first()
    if not project_find:
        raise HTTPException(status_code=400, detail="Project not found")
    if not user.is_admin and not session.exec(select(db_models.ProjectUserMembership).where(db_models.ProjectUserMembership.project_id == project_find.id, db_models.ProjectUserMembership.user_id == user.id)).first() and project_find.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not allowed to see Total quota for this project")
    return calculate_project_quota(project_find)

@router.get("/project/{project_name}/adjustements", tags=["quota"])
def show_project_adjustements(
        project_name: str,
        user: Annotated[db_models.User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> List[api_models.AdjustProjectQuotaID]:
    """Show all adjustements for a project"""
    project_find = session.exec(select(db_models.Project).where(db_models.Project.name == project_name)).first()
    if not project_find:
        raise HTTPException(status_code=400, detail="Project not found")
    if not user.is_admin and not session.exec(select(db_models.ProjectUserMembership).where(db_models.ProjectUserMembership.project_id == project_find.id, db_models.ProjectUserMembership.user_id == user.id)).first() and project_find.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not allowed to see Adjustements for this project")
    
    shared_quotas = []
    for q in session.exec(select(db_models.UserQuotaShare).where(db_models.UserQuotaShare.project_id == project_find.id)).all():
        user = session.exec(select(db_models.User).where(db_models.User.id == q.user_id)).first()
        shared_quotas.append(api_models.AdjustProjectQuotaID(
            id=q.id,
            username=user.username,
            project_name=project_find.name,
            type=db_models.QuotaType.from_str(q.type),
            quantity=q.quantity,
            comment=q.comment
        ))
    return shared_quotas

@router.get("/project/{project_name}/sync", tags=["quota"])
def api_sync_project(
        project_name: str,
        user: Annotated[db_models.User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> None:
    """Sync project quota with adjustements"""
    project_find = session.exec(select(db_models.Project).where(db_models.Project.name == project_name)).first()
    if not project_find:
        raise HTTPException(status_code=400, detail="Project not found")
    if not user.is_admin and project_find.owner_id != user.id and not session.exec(select(db_models.ProjectUserMembership).where(db_models.ProjectUserMembership.project_id == project_find.id, db_models.ProjectUserMembership.user_id == user.id)).first():
        raise HTTPException(status_code=403, detail="Not allowed to sync project")
    sync_project_quota(project_find)
