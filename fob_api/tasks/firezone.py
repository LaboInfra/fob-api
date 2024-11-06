from firezone_client import generate_password, generate_key_pair
from firezone_client import User as VpnUser
from firezone_client import Device as VpnDevice
from firezone_client import Rule as VpnRule
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
def get_rules_for_user(username: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise Exception("User not found")
        vpn_user_id: VpnUser = create_user(username)
        rules = firezone_driver.list(VpnRule)
        return [
            {
                "id": rule.id,
                "destination": rule.destination,
                "action": rule.action,
                "user_id": rule.user_id
            }
            for rule in rules
            if vpn_user_id == rule.user_id
        ]

@celery.task()
def sync_user_rules(username: str):
    """
    Sync all rules
        - delete rules that are not in allowed subnets
        - delete all rules if user is disabled
        - create rules for all allowed subnets
    """
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise Exception("User not found")
        vpn_user_id: VpnUser = create_user(username)
        allowed_subnets = user.allowed_subnets.split(",")
        rules_in_project = get_rules_for_user(username)

        # delete not wanted rules
        for rule in rules_in_project:
            if rule["destination"] not in allowed_subnets or user.disabled:
                rule_id = rule["id"]
                print(f"Deleting rule {rule_id} for user {username} as it is not in allowed subnets or user is disabled")
                rule_obj = firezone_driver.get(VpnRule, id=rule["id"])
                firezone_driver.delete(rule_obj)

        # create new rules
        for subnet in allowed_subnets:
            if user.disabled:
                break
            if subnet == "":
                continue
            if not any(rule["destination"] == subnet for rule in rules_in_project):
                print(f"Creating rule for subnet {subnet} for user {username}")
                firezone_driver.create(VpnRule(
                    user_id=vpn_user_id,
                    destination=subnet,
                    action="accept"
                ))

        return get_rules_for_user(username)


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