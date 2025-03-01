from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from novaclient import exceptions as nova_exceptions
from cinderclient import exceptions as cinder_exceptions

from fob_api import auth, openstack, random_end_uid, OPENSTACK_DOMAIN_ID, OPENSTACK_ROLE_MEMBER_ID, random_password, get_session
from fob_api.models.database import User, Project, ProjectUserMembership # deprecated import for models
from fob_api.models import database as db_models
from fob_api.models import api as api_models
from fob_api.models.api import OpenStackProject as OpenStackProjectAPI # deprecated import for models
from fob_api.models.api import OpenStackUserPassword as OpenStackUserPasswordAPI # deprecated import for models
from fob_api.tasks.openstack import get_or_create_user as openstack_get_or_create_user
from fob_api.tasks.openstack import set_user_password as openstack_set_user_password
from fob_api.tasks import openstack as openstack_tasks

router = APIRouter(prefix="/openstack")

MAX_PROJECTS_USER_OWN = 3

@router.get("/projects/{username}", tags=["openstack"])
def list_openstack_project_for_user(
        username: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> List[OpenStackProjectAPI]:
    """
    Return list of OpenStack projects for a user
    """
    auth.is_admin_or_self(user, username)
    user_find = session.exec(select(User).where(User.username == username)).first()
    projects_owner = session.exec(select(Project).where(Project.owner_id == user_find.id)).all()
    # get all owner projects
    data = []
    for project in projects_owner:
        db_members = session.exec(select(ProjectUserMembership).where(ProjectUserMembership.project_id == project.id)).all()
        data.append(OpenStackProjectAPI(
            id=project.id,
            name=project.name,
            owner=username,
            members=[
                session.exec(select(User).where(User.id == member.user_id)).first().username
                for member in db_members
            ]
        ))
    # get all member projects and add to data
    project_memberships = session.exec(select(ProjectUserMembership).where(ProjectUserMembership.user_id == user_find.id)).all()
    for project_membership in project_memberships:
        local_project = session.exec(select(Project).where(Project.id == project_membership.project_id)).first()
        db_members = session.exec(select(ProjectUserMembership).where(ProjectUserMembership.project_id == local_project.id)).all()
        owner = session.exec(select(User).where(User.id == local_project.owner_id)).first()
        data.append(OpenStackProjectAPI(
            id=local_project.id,
            name=local_project.name,
            owner=owner.username,
            members=[
                session.exec(select(User).where(User.id == member.user_id)).first().username
                for member in db_members
            ]
        ))
    return data

@router.post("/projects/{project_name}", tags=["openstack"])
def create_openstack_project(
        project_name: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> api_models.OpenStackProject | None:
    """
    Create a new OpenStack project
    """
    openstack_client = openstack.get_keystone_client()
    
    projects = session.exec(select(Project).where(Project.owner_id == user.id)).all()
    if len(projects) >= MAX_PROJECTS_USER_OWN:
        raise HTTPException(status_code=400, detail=f"You cannot create more than {str(MAX_PROJECTS_USER_OWN)} projects")
    project_name = project_name + "-" + random_end_uid()
    new_project = Project(name=project_name, owner_id=user.id)
    session.add(new_project)

    os_project = openstack_client.projects.create(name=new_project.name, domain=OPENSTACK_DOMAIN_ID, enabled=True)
    os_user = openstack_get_or_create_user(user.username)
    openstack_client.roles.grant(role=OPENSTACK_ROLE_MEMBER_ID, user=os_user.id, project=os_project.id)

    session.commit()
    session.refresh(new_project)
    return OpenStackProjectAPI(
        id=new_project.id,
        name=new_project.name,
        type="owner"
    )

@router.delete("/projects/{project_name}", tags=["openstack"])
def delete_openstack_project(
        project_name: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> None:
    """
    Delete an OpenStack project
    """
    openstack_client = openstack.get_keystone_client()
    project = session.exec(select(Project).where(Project.name == project_name)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to delete this project")
    
    # check if quota is given to project
    # here we are checking if project has any quotas assigned to it so nothing is left behind not assigned to any project
    project_quotas = session.exec(select(db_models.UserQuotaShare).where(db_models.UserQuotaShare.project_id == project.id)).all()
    for project_quota in project_quotas:
        if project_quota.quantity > 0:
            print(project_quota.quantity)
            raise HTTPException(status_code=400, detail="Cannot delete project with quotas assigned to it please remove all quotas assigned to project")

    # check if project has members
    project_memberships = session.exec(select(db_models.ProjectUserMembership).where(db_models.ProjectUserMembership.project_id == project.id)).all()
    if project_memberships:
        raise HTTPException(status_code=400, detail="Cannot delete project with members please remove all members from project")

    openstack_project = openstack_client.projects.find(name=project_name)
    openstack_client.projects.delete(openstack_project.id)
    session.delete(project)
    session.commit()

@router.put("/users/{username}/reset-password", tags=["openstack"])
def reset_openstack_user_password(
        username: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> OpenStackUserPasswordAPI:
    """
    Reset OpenStack user password
    """
    auth.is_admin_or_self(user, username)
    user_find = session.exec(select(User).where(User.username == username)).first()
    if not user_find:
        raise HTTPException(status_code=404, detail="User not found")
    rand_password = random_password()
    openstack_set_user_password(username, rand_password)
    return OpenStackUserPasswordAPI(username=username, password=rand_password)

@router.put("/projects/{project_name}/users/{username}", tags=["openstack"])
def add_user_to_project(
        project_name: str,
        username: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> None:
    """
    Add user to project
    """
    db_project = session.exec(select(Project).where(Project.name == project_name)).first()
    # check if owner of the project or is admin
    if db_project.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to add user to this project")

    # reject if user is owner of the project
    if user.username == username and db_project.owner_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot add owner to project (owner is already in project)")

    # get user to add
    user_to_add = session.exec(select(User).where(User.username == username)).first()
    if not user_to_add or not db_project:
        raise HTTPException(status_code=404, detail="User to add not found")
    
    # check if user is already in project
    assignment = session.exec(select(ProjectUserMembership).where(ProjectUserMembership.project_id == db_project.id, ProjectUserMembership.user_id == user_to_add.id)).first()
    if assignment:
        raise HTTPException(status_code=400, detail="User already in project")
    
    new_assignment = ProjectUserMembership(project_id=db_project.id, user_id=user_to_add.id)
    session.add(new_assignment)
    openstack_client = openstack.get_keystone_client()
    try:
        os_project = openstack_client.projects.find(name=project_name)
    except Exception:
        raise HTTPException(status_code=500, detail="OpenStack error cant get project")
    os_user = openstack_get_or_create_user(username)
    openstack_client.roles.grant(role=OPENSTACK_ROLE_MEMBER_ID, user=os_user.id, project=os_project.id)
    session.commit()

@router.delete("/projects/{project_name}/users/{username}", tags=["openstack"])
def remove_user_from_project(
        project_name: str,
        username: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> None:
    """
    Remove user from project
    """
    # check if owner of the project or is admin
    db_project = session.exec(select(Project).where(Project.name == project_name)).first()
    db_project_members_name = [
        session.exec(select(User).where(User.id == member.user_id)).first().username
        for member in session.exec(select(ProjectUserMembership).where(ProjectUserMembership.project_id == db_project.id)).all()
    ]

    # action allowed if anyone of the following is true
    # 1. user is admin
    # 2. user is owner of the project and wants to remove other user
    # 3. user is not owner of the project and wants to remove himself from project

    if db_project.owner_id != user.id and not user.is_admin and user.username not in db_project_members_name:
        raise HTTPException(status_code=403, detail="Not allowed to remove user from this project")
    
    if user.username in db_project_members_name:
        # this avoids the case where user is not owner of the project and wants to remove other user
        username = user.username
    
    # reject if user is owner of the project
    if user.username == username and db_project.owner_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from project (delete project instead)")

    # get user to remove    
    user_to_remove = session.exec(select(User).where(User.username == username)).first()
    if not user_to_remove or not db_project:
        raise HTTPException(status_code=404, detail="User not found")
    
    # check if user is already in project
    assignment = session.exec(select(ProjectUserMembership).where(ProjectUserMembership.project_id == db_project.id, ProjectUserMembership.user_id == user_to_remove.id)).first()
    if not assignment:
        raise HTTPException(status_code=400, detail="User not in project")
    
    # get project from openstack
    openstack_client = openstack.get_keystone_client()
    try:
        os_project = openstack_client.projects.find(name=project_name)
    except Exception:
        raise HTTPException(status_code=500, detail="OpenStack error cant get project")
        
    os_project = openstack.get_keystone_client().projects.find(name=project_name)    
    # check if user has any quotas assigned to project
    project_quotas = session.exec(select(db_models.UserQuotaShare).where(db_models.UserQuotaShare.project_id == db_project.id, db_models.UserQuotaShare.user_id == user_to_remove.id)).all()
    # try to set all quotas to 0
    old_quotas_map = {k: 0 for k in db_models.QuotaType}
    for project_quota in project_quotas:
        old_quotas_map[project_quota.type] = project_quota.quantity
        project_quota.quantity = 0
        session.add(project_quota)
    session.commit()

    # try to sync quotas with openstack without user quotas if it fails rollback quotas
    try:
        openstack_tasks.sync_project_quota(os_project)
    except (nova_exceptions.ClientException, cinder_exceptions.ClientException) as e:
        # rollback quotas when quota sync fails (when quota is lower than current usage)
        for project_quota in project_quotas:
            session.refresh(project_quota)
            project_quota.quantity = old_quotas_map[project_quota.type]
            session.add(project_quota)
        session.commit()
        raise HTTPException(status_code=400, detail="Cannot remove user from project, user share used quotas with project")
    
    # remove user from project
    os_user = openstack_get_or_create_user(username)
    openstack_client.roles.revoke(role=OPENSTACK_ROLE_MEMBER_ID, user=os_user.id, project=os_project.id)
    session.delete(assignment)
    session.commit()
