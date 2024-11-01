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

    vpn_user_id = firezone.create_user(username)

    return vpn_user_id