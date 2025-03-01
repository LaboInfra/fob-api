from datetime import datetime

from sqlmodel import Session, select
from fob_api import engine

from fob_api.models.database import User, Token
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

@celery.task(name="fastonboard.token.purge_expired")
def purge_expired_tokens():
    """
    Purge expired tokens from the database
    """
    with Session(engine) as session:
      now = datetime.now()
      tokens: Token = list(session.exec(select(Token).where(Token.expires_at < now)))
      if tokens_len := len(tokens) == 0:
        print("No expired tokens found")
        return 0
      print(f"Found {tokens_len} expired tokens deleting...")
      for token in tokens:
        print(f"Deleting token {token.token_id}")
        session.delete(token)
      session.commit()
    return tokens_len
