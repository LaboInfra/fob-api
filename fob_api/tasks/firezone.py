from os import environ
from firezone_client import FZClient, generate_password, generate_key_pair
from firezone_client import User as VpnUser
from firezone_client import Device as VpnDevice
from fob_api.models.user import User
from fob_api.worker import celery


FIREZONE_ENDPOINT = environ.get('FIREZONE_ENDPOINT')
FIREZONE_TOKEN = environ.get('FIREZONE_TOKEN')

if not FIREZONE_ENDPOINT or not FIREZONE_TOKEN:
    raise Exception("Missing FIREZONE_ENDPOINT or FIREZONE_TOKEN in environment variables")

vpn = FZClient(
    endpoint=environ.get('FIREZONE_ENDPOINT'),
    token=environ.get('FIREZONE_TOKEN')
)

@celery.task()
def create_user(user: User):
    try:
        user: VpnUser = vpn.get(VpnUser, id=user.email)
    except Exception:
        user = VpnUser(
            id=user.email,
            password=generate_password()
        )
        vpn.create(user)
    return user.id

@celery.task()
def get_devices_for_user(user: User):
    user_vpn: VpnUser = vpn.get(VpnUser, id=user.email)
    all_devices = vpn.list(VpnUser)
    return [device for device in all_devices if user_vpn.id == device.users]

@celery.task()
def create_device(user: User, allowed_ips: list[str]):
    user_vpn: VpnUser = vpn.get(VpnUser, id=user.email)
    public_key, private_key = generate_key_pair()
    device = VpnDevice(
        id=user_vpn.id,
        public_key=public_key,
        allowed_ips=allowed_ips,
        use_default_allowed_ips=False
    )
    vpn.create(device)
    return device