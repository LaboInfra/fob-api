from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship


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
    tokens: list["Token"] = Relationship(back_populates="user", cascade_delete=True)

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
    user: "User" = Relationship(back_populates="tokens")
