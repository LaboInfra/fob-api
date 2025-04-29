
from sqlmodel import select
from fob_api import OPENSTACK_DOMAIN_ID,random_password, OPENSTACK_ROLE_MEMBER_ID
from fob_api.config import Config
from fob_api.managers import UserManager
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client as keystone_client
from novaclient import client as nova_client
from neutronclient.v2_0 import client as neutron_client
from cinderclient import client as cinder_client
from fob_api.models import database as db_models
from fob_api.models import api as api_models

class OpenStackManager:

    session = None
    config = None
    
    def __init__(self, session = None):
        """
        Initialize the OpenStackManager with a database session.
        """
        if session:
            self.session = session
        self.config = Config()

    def __build_session(self):
        """
        Build a session for OpenStack authentication.
        :return: A session object for OpenStack authentication.
        """
        return session.Session(auth=v3.Password(
            auth_url=self.config.os_auth_url,
            username=self.config.os_username,
            password=self.config.os_password,
            project_name=self.config.os_project_name,
            user_domain_name=self.config.os_user_domain_name,
            project_domain_name=self.config.os_project_domain_name
        ), verify=False)

    def get_keystone_client(self) -> keystone_client.Client:
        """
        Returns a keystone client object.
        :return: A keystone client object.
        """
        return keystone_client.Client(session=self.__build_session())

    def get_nova_client(self) -> nova_client.Client:
        """
        Returns a nova client object.
        :return: A nova client object.
        """
        return nova_client.Client(2, session=self.__build_session())

    def get_neutron_client(self) -> neutron_client.Client:
        """
        Returns a neutron client object.
        :return: A neutron client object.
        """
        return neutron_client.Client(session=self.__build_session())

    def get_cinder_client(self) -> cinder_client.Client:
        """
        Returns a cinder client object.
        :return: A cinder client object.
        """
        return cinder_client.Client("3", session=self.__build_session())

    def get_or_create_user(self, username: str):
        """
        Create OpenStack User if not exists and return the user object.
        """
        user = UserManager(self.session).get_user_by_name(username)
        if not user:
            raise Exception("User not found")
        openstack_client = self.get_keystone_client()
        try:
            return openstack_client.users.find(name=user.username)
        except Exception:
            print(f"User {user.email} not found in OpenStack, creating...")
            openstack_client.users.create(name=user.username, password=random_password(), domain=OPENSTACK_DOMAIN_ID, enabled=True)
            return self.get_or_create_user(username)
    
    def set_user_password(self, username: str, password: str):
        """
        Set the password for an OpenStack user.
        """
        openstack_client = self.get_keystone_client()
        user = self.get_or_create_user(username)
        openstack_client.users.update(user=user, password=password)
    
    def calculate_user_quota_by_type(self, user: db_models.User, quota_type: db_models.QuotaType) -> api_models.AdjustUserQuota:
        calculated_quota = 0
        for q in self.session.exec(select(db_models.UserQuota).where(db_models.UserQuota.user_id == user.id).where(db_models.UserQuota.type == quota_type)).all():
            calculated_quota += q.quantity
        return api_models.AdjustUserQuota(
            username=user.username,
            type=quota_type,
            quantity=calculated_quota,
            comment="Calculated total quota for user"
        )

    def calculate_user_quota(self, user: db_models.User) -> list[api_models.AdjustUserQuota]:

        user_max_quota_dict = {k: 0 for k in db_models.QuotaType}
        for q in self.session.exec(select(db_models.UserQuota).where(db_models.UserQuota.user_id == user.id)).all():
            user_max_quota_dict[db_models.QuotaType.from_str(q.type)] += q.quantity

        return [api_models.AdjustUserQuota(
            username=user.username,
            type=k,
            quantity=v,
            comment="Calculated total all type quota for user"
        ) for k, v in user_max_quota_dict.items()]

    def calculate_project_quota(self, project: db_models.Project) -> list[api_models.AdjustProjectQuota]:

        project_max_quota_dict = {k: 0 for k in db_models.QuotaType}
        for q in self.session.exec(select(db_models.UserQuotaShare).where(db_models.UserQuotaShare.project_id == project.id)).all():
            project_max_quota_dict[db_models.QuotaType.from_str(q.type)] += q.quantity

        return [api_models.AdjustProjectQuota(
            username="",
            project_name=project.name,
            type=k,
            quantity=v,
            comment="Calculated total all type quota for project"
        ) for k, v in project_max_quota_dict.items()]

    def sync_project_quota(self, openstack_project: db_models.Project) -> None:
        nova_client = self.get_nova_client()
        cinder_client = self.get_cinder_client()
        keystone_client = self.get_keystone_client()

        project_id = keystone_client.projects.find(name=openstack_project.name).id

        for quota in self.calculate_project_quota(openstack_project):
            print(f"Syncing quota for project: {openstack_project.name} with type: {quota.type} and quantity: {quota.quantity}")
            match quota.type:
                case db_models.QuotaType.CPU:
                    nova_client.quotas.update(tenant_id=project_id, cores=quota.quantity)
                case db_models.QuotaType.MEMORY:
                    nova_client.quotas.update(tenant_id=project_id, ram=quota.quantity)
                case db_models.QuotaType.STORAGE:
                    cinder_client.quotas.update(tenant_id=project_id, gigabytes=quota.quantity)
                case _:
                    print(f"Unknown quota type: {quota.type} for project: {openstack_project.name} with quantity: {quota.quantity}")

    def get_user_left_quota_by_type(self, user: db_models.User, quota_type: db_models.QuotaType) -> int:
        user_quota_own = 0
        for q in self.session.exec(select(db_models.UserQuota).where(db_models.UserQuota.user_id == user.id).where(db_models.UserQuota.type == quota_type)).all():
            user_quota_own += q.quantity

        user_quota_used = 0
        for q in self.session.exec(select(db_models.UserQuotaShare).where(db_models.UserQuotaShare.user_id == user.id).where(db_models.UserQuotaShare.type == quota_type)).all():
            user_quota_used += q.quantity

        return user_quota_own - user_quota_used

    def get_project(self, project_name: str) -> db_models.Project | None:
        """
        Get project by name
        """
        return self.session.exec(select(db_models.Project).where(db_models.Project.name == project_name)).first()

    def get_keystone_project(self, project_name: str) -> keystone_client.projects.Project | None:
        """
        Get keystone project by name
        """
        keystone_client = self.get_keystone_client()
        try:
            return keystone_client.projects.find(name=project_name)
        except Exception:
            print(f"Project {project_name} not found in OpenStack")
            return None

    def is_user_member_of_project(self, user: db_models.User, project: db_models.Project) -> bool:
        """
        Check if user is member of project
        """
        return bool(session.exec(
            select(db_models.ProjectUserMembership)
            .where(db_models.ProjectUserMembership.project_id == project.id, db_models.ProjectUserMembership.user_id == user.id)
        ).first())

    def add_user_to_project(self, user: db_models.User, project: db_models.Project):
        """
        Add user to a project in DB and OpenStack
        """
        new_assignment = db_models.ProjectUserMembership(project_id=project.id, user_id=user.id)
        self.session.add(new_assignment)
        keystone_client = self.get_keystone_client()

        keystone_project = self.get_keystone_project(project.name)
        keystone_user = self.get_or_create_user(user.username)

        keystone_client.roles.grant(role=OPENSTACK_ROLE_MEMBER_ID, user=keystone_user.id, project=keystone_project.id)

        self.session.commit()

    def list_user_owner_projects(self, user: db_models.User) -> list[db_models.Project]:
        """
        List all projects owned by user
        """
        return self.session.exec(
            select(db_models.Project)
            .join(db_models.ProjectUserMembership)
            .where(db_models.ProjectUserMembership.user_id == user.id)
        ).all()

    def list_user_member_projects(self, user: db_models.User) -> list[db_models.Project]:
        """
        List all projects user is a member of
        """
        return self.session.exec(
            select(db_models.Project)
            .join(db_models.ProjectUserMembership)
            .where(db_models.ProjectUserMembership.user_id == user.id)
        ).all()