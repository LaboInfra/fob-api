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

    # TODO
    # Creation
    # 1 create user
    db_user: list[User] = session.exec(select(User)).all()
    openstack_users = keystone_client.users.list()

    db_user_names = [user.username for user in db_user if user.username not in BANNED_NAMES]
    openstack_user_names = [user.name for user in openstack_users if user.name not in BANNED_NAMES]
    
    user_to_create = [user for user in db_user if user.username not in openstack_user_names and user.username not in BANNED_NAMES]
    user_to_delete = [user for user in openstack_users if user.name not in db_user_names and user.name not in BANNED_NAMES]

    print("Creating missing users with random password:")
    for user in user_to_create:
        print(f"Creating user: {user.username}")
        keystone_client.users.create(name=user.username, password=random_password(), domain="default", enabled=True)
    print(f"Done")

    # 2 create project

    db_project: list[Project] = session.exec(select(Project)).all()
    openstack_projects = keystone_client.projects.list()

    db_project_names = [project.name for project in db_project]
    openstack_project_names = [project.name for project in openstack_projects]

    project_to_create = [project for project in db_project if project.name not in openstack_project_names and project.name not in BANNED_NAMES]
    project_to_delete = [project for project in openstack_projects if project.name not in db_project_names and project.name not in BANNED_NAMES]

    print("Creating missing projects:")
    for project in project_to_create:
        user = session.exec(select(User).where(User.id == project.owner_id)).first()
        print(f"Creating project: {project.name} with owner: {user.username}")
        keystone_client.projects.create(name=project.name, domain="default", enabled=True)
    print("Done")

    # 3 assign user to project
    db_assignments: list[ProjectUserMembership] = session.exec(select(ProjectUserMembership)).all()
    db_project: list[Project] = session.exec(select(Project)).all()

    # get required assignments from db
    merged_db_assignments = {}
    for project in db_project:
        if project.name not in merged_db_assignments:
            merged_db_assignments[project.name] = set()
        user = session.exec(select(User).where(User.id == project.owner_id)).first()
        merged_db_assignments[project.name].add(user.username)
    
    for assignment in db_assignments:
        user = session.exec(select(User).where(User.id == assignment.user_id)).first()
        project = session.exec(select(Project).where(Project.id == assignment.project_id)).first()
        merged_db_assignments[project.name].add(user.username)

    # get assignment from openstack 
    merged_openstack_assignments = {}
    for assignment in keystone_client.role_assignments.list():
        if "project" not in assignment.scope:
            continue
        
        project = keystone_client.projects.get(assignment.scope["project"]["id"]).name
        username = keystone_client.users.get(assignment.user["id"]).name

        if project in BANNED_NAMES or username in BANNED_NAMES:
            continue

        if project not in merged_openstack_assignments:
            merged_openstack_assignments[project] = set()
        merged_openstack_assignments[project].add(username)

    # give permission based on required assignments on db
    print("Assigning missing users to projects:")
    for project_name, users in merged_db_assignments.items():
        for user in users:
            if project_name in merged_openstack_assignments and user in merged_openstack_assignments[project_name]:
                continue
            print(f"\t user: {user} to project: {project_name}")
            openstack_user = keystone_client.users.find(name=user)
            openstack_project = keystone_client.projects.find(name=project_name)
            keystone_client.roles.grant(role=OPENSTACK_ROLE_MEMBER, user=openstack_user, project=openstack_project)
    print("Done")

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
    
    # make inverstigation on limits system and create a nova endpoint to test quota assignement
    #print(keystone_client.limits.list())
    # assign quota to project
    #for project in session.exec(select(Project)).all():
    #    project_quota_to_apply_dict = {k: 0 for k in QuotaType}
    #    for q in session.exec(select(UserQuotaShare).where(UserQuotaShare.project_id == project.id)).all():
    #        project_quota_to_apply_dict[QuotaType.from_str(q.type)] += q.quantity
    #    print(f"Quota to apply for project: {project.name}")
    #    print(project_quota_to_apply_dict)
    #    openstack_project = keystone_client.projects.find(name=project.name)
    #    for k, v in project_quota_to_apply_dict.items():
    #        #keystone_client.projects.update_quota(openstack_project, k.value, v)
            

    # Deletion
    # try remove quota from project WARNING: check if quota is not used Or how can react nova if set under current usage

    # try remove user from project cant remove if user is owner
    print("Removing users from projects:")
    for project_name, users in merged_openstack_assignments.items():
        for user in users:
            if project_name not in merged_db_assignments or user not in merged_db_assignments[project_name]:
                print(f"\t user: {user} from project: {project_name}")
                openstack_user = keystone_client.users.find(name=user)
                openstack_project = keystone_client.projects.find(name=project_name)
                keystone_client.roles.revoke(role=OPENSTACK_ROLE_MEMBER, user=openstack_user, project=openstack_project)
    
    # try remove project
    print("Removing projects:")
    for project in project_to_delete:
        if project.name in BANNED_NAMES:
            continue
        print(f"Removing project: {project.name}")
        openstack_project = keystone_client.projects.find(name=project.name)
        keystone_client.projects.delete(openstack_project)


    # try remove user
    print("Removing users:")
    for user in user_to_delete:
        if user.name in BANNED_NAMES:
            continue
        print(f"Removing user: {user.name}")
        openstack_user = keystone_client.users.find(name=user.name)
        keystone_client.users.delete(openstack_user)
