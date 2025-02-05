from datetime import datetime
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """
    This class represents the User for all the system of laboinfra
    """
    id: int = Field(primary_key=True)
    username: str = Field(unique=True)
    password: str
    email: str = Field(unique=True)
    is_admin: bool = False
    disabled: bool = False
    last_synced: datetime = Field(default=datetime.now())

class UserPasswordReset(SQLModel, table=True):
    """
    This class represents the UserPasswordReset request
    """
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    token: str
    source_ip: str
    created_at: datetime = Field(default=datetime.now())
    expires_at: datetime

class Token(SQLModel, table=True):
    """
    This class represents the Token
    """
    id: int = Field(primary_key=True)
    expires_at: datetime
    created_at: datetime
    token_id: str
    user_id: int = Field(foreign_key="user.id")
