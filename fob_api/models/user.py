from datetime import datetime
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """
    This class represents the User for all the system of laboinfra
    """
    id: int = Field(primary_key=True)
    username: str
    password: str
    email: str
    is_admin: bool = False
    disabled: bool = False
    last_synced: datetime = Field(default=datetime.now())
    allowed_subnets: str = Field(default="")

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
