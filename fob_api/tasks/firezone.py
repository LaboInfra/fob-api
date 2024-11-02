from firezone_client import generate_password, generate_key_pair
from firezone_client import User as VpnUser
from firezone_client import Device as VpnDevice
from sqlmodel import Session, select

from fob_api.models.user import User
from fob_api.worker import celery
from fob_api import engine
from fob_api.vpn import firezone_driver


@celery.task()
def create_user(username: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise Exception("User not found")
        try:
            vpn_user: VpnUser = firezone_driver.get(VpnUser, id=user.email)
        except Exception:
            print(f"User {user.email} not found in Firezone VPN, creating...")
            firezone_driver.create(VpnUser(
                email=user.email,
                password=generate_password(24)
            ))
            return create_user(username)
        return vpn_user.id

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