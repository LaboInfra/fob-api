"""
# THIS CODE IS DEPRECATED USER OPENSTACKMANAGER INSTEAD
This module is used to authenticate with OpenStack and create a client object.
"""

from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client as keystone_client
from novaclient import client as nova_client
from neutronclient.v2_0 import client as neutron_client
from cinderclient import client as cinder_client

from fob_api import Config

def get_session() -> session.Session:

    config = Config()

    keystone_auth = v3.Password(
        auth_url=config.os_auth_url,
        username=config.os_username,
        password=config.os_password,
        project_name=config.os_project_name,
        user_domain_name=config.os_user_domain_name,
        project_domain_name=config.os_project_domain_name
    )

    return session.Session(auth=keystone_auth, verify=False)

def get_keystone_client() -> keystone_client.Client:
    """
    Returns a keystone client object.
    """
    return keystone_client.Client(session=get_session())

def get_nova_client() -> nova_client.Client:
    """
    Returns a nova client object.
    """
    return nova_client.Client(2, session=get_session())

def get_neutron_client() -> neutron_client.Client:
    """
    Returns a neutron client object.
    """
    return neutron_client.Client(session=get_session())

def get_cinder_client() -> cinder_client.Client:
    """
    Returns a cinder client object.
    """
    return cinder_client.Client("3", session=get_session())
