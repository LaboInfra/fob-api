from dotenv import load_dotenv
from pydantic import BaseModel

from .database import init_engine

class TaskInfo(BaseModel):
    id: str
    status: str
    result: str | None

load_dotenv()
engine = init_engine()