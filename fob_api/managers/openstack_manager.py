from fob_api.config import Config
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client as keystone_client
from novaclient import client as nova_client
from neutronclient.v2_0 import client as neutron_client
from cinderclient import client as cinder_client


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

    def _build_session(self):
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
        return keystone_client.Client(session=self._build_session())

    def get_nova_client(self) -> nova_client.Client:
        """
        Returns a nova client object.
        :return: A nova client object.
        """
        return nova_client.Client(2, session=self._build_session())

    def get_neutron_client(self) -> neutron_client.Client:
        """
        Returns a neutron client object.
        :return: A neutron client object.
        """
        return neutron_client.Client(session=self._build_session())

    def get_cinder_client(self) -> cinder_client.Client:
        """
        Returns a cinder client object.
        :return: A cinder client object.
        """
        return cinder_client.Client("3", session=self._build_session())