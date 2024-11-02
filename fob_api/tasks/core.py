from datetime import datetime

from requests import Session
from sqlalchemy import select
from fob_api import engine
from fob_api.models.user import User
from fob_api.worker import celery
from fob_api.tasks import firezone

@celery.task()
def sync_user(username: str):
    """
    Sync user with all external services
      - Config Firezone VPN
      - TODO Config UserInKeyStone
    """
    with Session(engine) as session:
      user: User = session.exec(select(User).filter(User.username == username)).first()
      if not user:
         raise ValueError(f"User {username} not found")
      user.last_synced = datetime.now()
      vpn_user_id = firezone.create_user(username)      
      session.add(user)
      session.commit()
      session.refresh(user)

    return vpn_user_id
