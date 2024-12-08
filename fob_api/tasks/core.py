from datetime import datetime

from sqlmodel import Session, select
from fob_api import engine

from fob_api.models.database import User
from fob_api.worker import celery
from fob_api.tasks import headscale
from fob_api.models.api import SyncInfo

@celery.task()
def sync_user(username: str):
    """
    Sync user with all external services
      - Config HeadScale VPN
      - TODO Config UserInKeyStone
    """
    with Session(engine) as session:
      statement = select(User).where(User.username == username)
      results = session.exec(statement)
      user = results.one()
      user.last_synced = datetime.now()
      vpn_user = headscale.create_user(username)
      #allowed_subnets = .sync_user_rules(username)      
      session.add(user)
      session.commit()
      session.refresh(user)
    
    return SyncInfo(
        username=user.username,
        firezone_account_id=str(vpn_user_id),
        allowed_subnets=allowed_subnets,
        last_synced=user.last_synced.isoformat()
    )

    return {
      "username": user.username,
      "vpn": vpn_user,
      "allowed_subnets": "Not implemented",
      "last_synced": user.last_synced
    }
