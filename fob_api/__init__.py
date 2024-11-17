from pydantic import BaseModel

from .config import Config
from .database import init_engine

class TaskInfo(BaseModel):
    id: str
    status: str
    result: str | dict | None

# Initialize configuration and database engine
Config()
engine = init_engine()