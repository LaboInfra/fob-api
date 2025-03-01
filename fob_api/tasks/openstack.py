from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from fob_api import engine, openstack, random_end_uid, random_password, OPENSTACK_DOMAIN_ID
from fob_api.models.database import User # deprecated call use db_models as prefix
from fob_api.models import database as db_models

def get_or_create_user(username: str): # todo return openstack user object
    """
    Create OpenStack User if not exists

    Args:
        username (str): User name

    Returns:
        openstack user object
    """
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise Exception("User not found")
        openstack_client = openstack.get_keystone_client()
        try:
            return openstack_client.users.find(name=user.username)
        except Exception:
            print(f"User {user.email} not found in OpenStack, creating...")
            openstack_client.users.create(name=user.username, password=random_password(), domain=OPENSTACK_DOMAIN_ID, enabled=True)
            return get_or_create_user(username)

def set_user_password(username: str, password: str) -> None:
    openstack_client = openstack.get_keystone_client()
    user = get_or_create_user(username)
    openstack_client.users.update(user=user, password=password)

def sync_project_quota(openstack_project: db_models.Project) -> None:
    """
    Temp warp function to the correct function
    """
    # temporary for how long? who knows write 01-03-2025 19:19
    from fob_api.routes.quota import sync_project_quota as sync_project_quota_real
    sync_project_quota_real(openstack_project)
