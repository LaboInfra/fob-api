from .config import Config
from .database import init_engine
from . import mail

# Initialize configuration and database engine
engine = init_engine()
