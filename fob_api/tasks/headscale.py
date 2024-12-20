from sqlmodel import Session, select
from uuid import UUID

from fob_api.models.database import User
from fob_api.worker import celery
from fob_api import engine, headscale_driver
from fob_api.lib.headscale import PolicyACL, PolicyData

from fob_api.models.database import (
    HeadScalePolicyACL,
    HeadScalePolicyHost,
    HeadScalePolicyGroupMember,
    HeadScalePolicyTagOwnerMember
)

def create_user(username: str):
    """
    Create User namescpaces in HeadScale Controller

    Returns: HeadScale User object
    """
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise Exception("User not found")
        try:
            return headscale_driver.user.get(name=user.username)
        except Exception:
            print(f"User {user.email} not found in HeadScale VPN, creating...")
            headscale_driver.user.create(name=user.username)
            return create_user(username)

def build_headscale_policy_from_db() -> PolicyData:
    """
    Build HeadScale Policy Data from Database
    
    Used to update HeadScale Policy Data
    """

    new_pldt = PolicyData()

    with Session(engine) as session:
        new_pldt.hosts = {host.name: host.ip for host in session.exec(select(HeadScalePolicyHost)).all()}
        
        for group in session.exec(select(HeadScalePolicyGroupMember)).all():
            group_name = "group:" + group.name
            if group_name not in new_pldt.groups:
                new_pldt.groups[group_name] = []
            new_pldt.groups[group_name].append(group.member)

        for tag in session.exec(select(HeadScalePolicyTagOwnerMember)).all():
            tag_name = "tag:" + tag.name
            if tag_name not in new_pldt.tagOwners:
                new_pldt.tagOwners[tag_name] = []
            new_pldt.tagOwners[tag_name].append(tag.member)

        for acl in session.exec(select(HeadScalePolicyACL)).all():
            new_pldt.acls.append(
                PolicyACL(
                    action=acl.action,
                    src=acl.src.split(","),
                    dst=acl.dst.split(","),
                    proto=acl.proto
                )
            )
    return new_pldt

@celery.task(name="fastonboard.headscale.sync_policy")
def update_headscale_policy() -> tuple:
    """
    Update HeadScale Policy Data from Database if there are changes
    """
    new_pldt = build_headscale_policy_from_db()
    old_pldt_str = headscale_driver.policy.dump(headscale_driver.policy.get_policy_data())
    new_pldt_str = headscale_driver.policy.dump(new_pldt)
    if old_pldt_str != new_pldt_str:
        headscale_driver.policy.update(new_pldt)
        print("HeadScale Policy data has been updated")
        return old_pldt_str, new_pldt_str
    print("HeadScale Policy data is up to date")
    return None, None
