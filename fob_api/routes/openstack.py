from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from fob_api import auth, openstack, random_end_uid, OPENSTACK_DOMAIN_ID, OPENSTACK_ROLE_MEMBER_ID, random_password, get_session
from fob_api.models.database import User, Project, ProjectUserMembership
from fob_api.models.api import OpenStackProject as OpenStackProjectAPI
from fob_api.models.api import OpenStackProjectCreate as OpenStackProjectCreateAPI
from fob_api.models.api import OpenStackUserPassword as OpenStackUserPasswordAPI
from fob_api.tasks.openstack import get_or_create_user as openstack_get_or_create_user
from fob_api.tasks.openstack import set_user_password as openstack_set_user_password


router = APIRouter(prefix="/openstack")

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
    projects = session.exec(select(Project).where(Project.owner_id == user_find.id)).all()
    return [OpenStackProjectAPI(
        id=project.id,
        name=project.name
    ) for project in projects]

@router.post("/projects/{project_name}", tags=["openstack"])
def create_openstack_project(
        project_name: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> OpenStackProjectAPI | None:
    """
    Create a new OpenStack project
    """
    openstack_client = openstack.get_keystone_client()
    
    projects = session.exec(select(Project).where(Project.owner_id == user.id)).all()
    if len(projects) >= 3:
        raise HTTPException(status_code=400, detail="You cannot create more than 3 projects")
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
        name=new_project.name
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
    Add user to project if user is owner of the project
    """
    db_project = session.exec(select(Project).where(Project.name == project_name)).first()
    if db_project.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to add user to this project")
    
    user_to_add = session.exec(select(User).where(User.username == username)).first()
    if not user_to_add or not db_project:
        raise HTTPException(status_code=404, detail="User or project not found")

    # if user is owner of the project
    if user_to_add.id == db_project.owner_id:
        raise HTTPException(status_code=400, detail="User is owner of the project do not need to be added")
    
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
    Remove user from project if user is owner of the project
    """
    db_project = session.exec(select(Project).where(Project.name == project_name)).first()
    if db_project.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to remove user from this project")
    
    user_to_remove = session.exec(select(User).where(User.username == username)).first()
    if not user_to_remove or not db_project:
        raise HTTPException(status_code=404, detail="User or project not found")
    
    # check if user is owner of the project
    if db_project.owner_id == user_to_remove.id:
        raise HTTPException(status_code=400, detail="Cannot remove owner from project")
    
    # check if user is already in project
    assignment = session.exec(select(ProjectUserMembership).where(ProjectUserMembership.project_id == db_project.id, ProjectUserMembership.user_id == user_to_remove.id)).first()
    if not assignment:
        raise HTTPException(status_code=400, detail="User not in project")
    
    session.delete(assignment)
    openstack_client = openstack.get_keystone_client()
    try:
        os_project = openstack_client.projects.find(name=project_name)
    except Exception:
        raise HTTPException(status_code=500, detail="OpenStack error cant get project")
    os_user = openstack_get_or_create_user(username)
    openstack_client.roles.revoke(role=OPENSTACK_ROLE_MEMBER_ID, user=os_user.id, project=os_project.id)
    session.commit()
