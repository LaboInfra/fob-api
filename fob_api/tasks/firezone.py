from firezone_client import generate_password, generate_key_pair
from firezone_client import User as VpnUser
from firezone_client import Device as VpnDevice
from firezone_client import Rule as VpnRule
from sqlmodel import Session, select
from uuid import UUID

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
def get_devices_for_user(username: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise Exception("User not found")

        user_vpn_id: VpnUser = create_user(username)
        all_devices: list[VpnDevice] = firezone_driver.list(VpnDevice)
        return [
            device
            for device in all_devices
            if user_vpn_id == device.user_id
        ]

@celery.task()
def create_device(username, device_name):
    with Session(engine) as session:
        user: User = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise Exception("User not found")
        if len(user.allowed_subnets) == 0:
            return {
                "status": "rejected",
                "message": "User has no allowed subnets"
            }
        
        devices = get_devices_for_user(username)
        if len(devices) > 5:
            return {
                "status": "rejected",
                "message": "User has too many devices"
            }
        for device in devices:
            if device.name == device_name:
                return {
                    "status": "rejected",
                    "message": "Device with that name already exists"
                }

        user_vpn_id: VpnUser = create_user(username)
        public_key, private_key = generate_key_pair()
        device = VpnDevice(
            name=device_name,
            user_id=user_vpn_id,
            public_key=public_key,
            allowed_ips=user.allowed_subnets.split(","),
            use_default_allowed_ips=False
        )
        firezone_driver.create(device)
        
        for device in get_devices_for_user(username):
            if device.name == device_name:
                return {
                    "status": "success",
                    "message": "Device created",
                    "private_key": private_key,
                    "device": device.__dict__
                }
        return {
            "status": "error",
            "code_tag": "THIS_SHOULD_NOT_HAPPEN_DEVICE_CREATION"
        }
