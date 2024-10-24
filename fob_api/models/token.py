from datetime import datetime
from fastapi.security import HTTPBasicCredentials
from sqlmodel import Field, SQLModel, Session, select

from fob_api import engine
from fob_api.models.user import User

class Token(SQLModel, table=True):
    uuid: str = Field(primary_key=True)
    is_active: bool = True
    