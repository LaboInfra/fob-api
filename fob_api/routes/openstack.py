from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from fob_api import auth, engine, openstack, random_end_uid, OPENSTACK_DOMAIN_ID, OPENSTACK_ROLE_MEMBER_ID
from fob_api.models.database import User, Project
from fob_api.models.api import OpenStackProject as OpenStackProjectAPI
from fob_api.models.api import OpenStackProjectCreate as OpenStackProjectCreateAPI
from fob_api.tasks.openstack import get_or_create_user as openstack_get_or_create_user


router = APIRouter(prefix="/openstack")

@router.get("/projects/{username}", tags=["openstack", "admin"])
def list_openstack_project_for_user(username: str, user: Annotated[User, Depends(auth.get_current_user)]) -> List[OpenStackProjectAPI]:
    """
    Return list of OpenStack projects for a user
    """
    if not user.is_admin and user.username != username:
        raise HTTPException(status_code=403, detail="Not allowed to view projects for this user")
    with Session(engine) as session:
        user_find = session.exec(select(User).where(User.username == username)).first()
        projects = session.exec(select(Project).where(Project.owner_id == user_find.id)).all()
    return [OpenStackProjectAPI(
        id=project.id,
        name=project.name
    ) for project in projects]

@router.post("/projects/", tags=["openstack"])
def create_openstack_project(project: OpenStackProjectCreateAPI, user: Annotated[User, Depends(auth.get_current_user)]) -> OpenStackProjectAPI | None:
    """
    Create a new OpenStack project
    """
    openstack_client = openstack.get_keystone_client()
    
    with Session(engine) as session:
        projects = session.exec(select(Project).where(Project.owner_id == user.id)).all()
        if len(projects) >= 5:
            raise HTTPException(status_code=400, detail="You cannot create more than 5 projects")
        project_name = project.name + "-" + random_end_uid()
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
def delete_openstack_project(project_name: str, user: Annotated[User, Depends(auth.get_current_user)]) -> None:
    """
    Delete an OpenStack project
    """
    openstack_client = openstack.get_keystone_client()
    with Session(engine) as session:
        project = session.exec(select(Project).where(Project.name == project_name)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.owner_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not allowed to delete this project")
        openstack_project = openstack_client.projects.find(name=project_name)
        openstack_client.projects.delete(openstack_project.id)
        session.delete(project)
        session.commit()
    return None
