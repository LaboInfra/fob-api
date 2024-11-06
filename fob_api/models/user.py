from datetime import datetime
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """
    This class represents the User for all the system?

    in this app user cant create account themselves, only admin can create account for them and they need to enable the account by themselves
    """
    id: int = Field(primary_key=True)
    username: str
    password: str
    email: str
    is_admin: bool = False
    disabled: bool = False
    last_synced: datetime = Field(default=datetime.now())
    allowed_subnets: str = Field(default="")
