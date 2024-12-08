from pydantic import BaseModel

from .config import Config
from .database import init_engine
from .lib.headscale import HeadScale
from . import mail

class TaskInfo(BaseModel):
    id: str
    status: str
    result: str | dict | None

# Initialize configuration and database engine
engine = init_engine()
