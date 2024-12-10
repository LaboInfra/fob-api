"""
This module is used to authenticate with OpenStack and create a client object.
"""

from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client

from fob_api import Config

config = Config()

keystone_auth = v3.Password(
    auth_url=config.os_auth_url,
    username=config.os_username,
    password=config.os_password,
    project_name=config.os_project_name,
    user_domain_name=config.os_user_domain_name,
    project_domain_name=config.os_project_domain_name
)

keystone_session = session.Session(auth=keystone_auth)

keystone_client = client.Client(session=keystone_session)
