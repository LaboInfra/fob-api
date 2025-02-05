from .config import Config
from .database import init_engine, get_session
from .lib.headscale import HeadScale
from .vpn import headscale_driver
from . import mail
from uuid import uuid4
from random import choices
from string import ascii_letters, digits

import urllib3

urllib3.disable_warnings()

random_end_uid = lambda: str(uuid4()).split('-')[-1]
random_password = lambda: "".join(choices(ascii_letters + digits, k=16))

# TODO move to config
OPENSTACK_DOMAIN_ID = "cbd81d851be944aeb22873cc9919c82c"
OPENSTACK_ROLE_MEMBER_ID = "33db095e110f421487ad379176873aff"

# Initialize configuration and database engine
engine = init_engine()
