from datetime import datetime

from sqlmodel import Session, select
from fob_api import engine

from fob_api.models.database import User
from fob_api.worker import celery
from fob_api.tasks import headscale, openstack
from fob_api.models.api import SyncInfo

@celery.task()
def sync_user(username: str):
    """
    Sync user with all external services
      - Config HeadScale VPN
      - Config UserInKeyStone
    """
    with Session(engine) as session:
      statement = select(User).where(User.username == username)
      results = session.exec(statement)
      user = results.one()
      user.last_synced = datetime.now()
      headscale.get_or_create_user(username)
      openstack.get_or_create_user(username)
      headscale.add_user_to_group(username, "cloud-edge")
      session.add(user)
      session.commit()
      session.refresh(user)
    
    return SyncInfo(
        username=user.username,
        last_synced=user.last_synced.isoformat()
    )
