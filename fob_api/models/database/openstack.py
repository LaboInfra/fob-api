from enum import Enum as PyEnum
from datetime import datetime
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.sql.sqltypes import Enum

class QuotaType(str, PyEnum):
    """
    Enum for quota share types available in this API
    """
    CPU = "cpu"
    MEMORY = "mem"
    STORAGE = "sto"

class UserQuota(SQLModel, table=True):
    """
    Represents one quota adjustment for a user
    """
    __tablename__ = "openstack_user_quota"

    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id") # user whose quota is being adjusted
    comment: str = Field(nullable=True) # reason for this quota adjustment
    quantity: int = Field() # + for increase, - for decrease followed by a number
    type: QuotaType = Field(sa_column=Column(Enum(QuotaType))) # 'cpu', 'memory', 'storage'
    created_at: datetime = Field(default=datetime.now())

class Project(SQLModel, table=True):
    """
    Represents a project in OpenStack and its owned by a user
    """
    __tablename__ = "openstack_project"

    id: int = Field(primary_key=True)
    name: str = Field() # name of the project
    owner_id: int = Field(foreign_key="user.id") # user who owns this project
    created_at: datetime = Field(default=datetime.now())

class ProjectUserMembership(SQLModel, table=True):
    """
    Represents a user's membership in a project
    """
    __tablename__ = "openstack_project_user_membership"

    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    project_id: int = Field(foreign_key="openstack_project.id")
    created_at: datetime = Field(default=datetime.now())

class UserQuotaShare(SQLModel, table=True):
    """
    Represents a user's shared quota on a project
    """
    __tablename__ = "openstack_user_quota_share"

    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    project_id: int = Field(foreign_key="openstack_project.id")
    comment: str = Field(nullable=True)
    quantity: int = Field()
    type: QuotaType = Field(sa_column=Column(Enum(QuotaType)))
    created_at: datetime = Field(default=datetime.now())
