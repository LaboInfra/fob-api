"""
This is a development script to write the future function to implement on the api

Objective final for api with all function below:
- Sync the database of the api with the openstack keystone service
- Enable user to add user to project it owns
- Enable user to have dynamic quota for each project 
- Enable user to share quota with other project 

Currently this script is used to sync the database of the api with the openstack keystone service on following aspects: user, project, project user membership, user quota, project quota
"""

import urllib3

urllib3.disable_warnings()

from rich import print
from rich.traceback import install
install(show_locals=True)
from sqlmodel import select, Session
from fob_api import openstack, engine
from fob_api.models.database import QuotaType, UserQuota, UserQuotaShare, Project, ProjectUserMembership, User

keystone_client = openstack.get_keystone_client()

import random
import string
random_password = lambda: "".join(random.choices(string.ascii_letters + string.digits, k=16))

BANNED_NAMES = ["admin", "serivce"]
OPENSTACK_ROLE_MEMBER = keystone_client.roles.find(name="member")

with Session(engine) as session:
    # 4 assign quota to project
    users = session.exec(select(User).where(User.username != "admin")).all()
    for user in users:
        ## Calculate all quota for user with shared quota
        # extract max quota for user
        user_max_quota_dict = {k: 0 for k in QuotaType}
        for q in session.exec(select(UserQuota).where(UserQuota.user_id == user.id)).all():
            user_max_quota_dict[QuotaType.from_str(q.type)] += q.quantity
        print(f"Max quota for user: {user.username}")
        print(user_max_quota_dict)

        # extract quota who user share with project
        user_shared_quota_dict = {k: 0 for k in QuotaType}
        for q in session.exec(select(UserQuotaShare).where(UserQuotaShare.user_id == user.id)).all():
            user_shared_quota_dict[QuotaType.from_str(q.type)] += q.quantity

        print(f"Shared quota for user: {user.username}")
        print(user_shared_quota_dict)

        # calculate quota left for user
        user_left_quota_dict = {k: 0 for k in QuotaType}
        for k in user_max_quota_dict:
            user_left_quota_dict[k] = user_max_quota_dict[k] - user_shared_quota_dict[k]
        print(f"Left quota for user: {user.username}")
        print(user_left_quota_dict)
