from fob_api.models.user import User
from fob_api.worker import celery

@celery.task()
def sync_user(username: str):
    """
    Sync user with all external services
      - Config Firezone VPN
      - TODO Config UserInKeyStone
    """
    return "User synced"