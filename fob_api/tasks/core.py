from datetime import datetime

from sqlmodel import Session, select
from fob_api import engine

from fob_api.models.database import User
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
      statement = select(User).where(User.username == username)
      results = session.exec(statement)
      user = results.one()
      user.last_synced = datetime.now()
      vpn_user_id = firezone.create_user(username)
      allowed_subnets = firezone.sync_user_rules(username)      
      session.add(user)
      session.commit()
      session.refresh(user)

    return {
      "username": user.username,
      "firezone_account_id": vpn_user_id,
      "allowed_subnets": allowed_subnets,
      "last_synced": user.last_synced
    }
