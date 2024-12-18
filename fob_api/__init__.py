from .config import Config
from .database import init_engine
from .lib.headscale import HeadScale
from .vpn import headscale_driver
from . import mail

# Initialize configuration and database engine
engine = init_engine()
