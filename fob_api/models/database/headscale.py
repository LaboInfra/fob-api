from sqlmodel import Field, SQLModel, UniqueConstraint

class HeadScalePolicyACL(SQLModel, table=True):
    id: int = Field(primary_key=True)
    action: str
    src: str
    dst: str
    proto: str = Field(nullable=True)

class HeadScalePolicyGroupMember(SQLModel, table=True):

    __table_args__ = (
        UniqueConstraint("name", "member", name="unique_group_name_member"),
    )

    id: int = Field(primary_key=True)
    name: str
    member: str

class HeadScalePolicyTagOwnerMember(SQLModel, table=True):

    __table_args__ = (
        UniqueConstraint("name", "member", name="unique_owner_tag_name_member"),
    )

    id: int = Field(primary_key=True)
    name: str
    member: str


class HeadScalePolicyHost(SQLModel, table=True):

    __table_args__ = (
        UniqueConstraint("name", "ip", name="unique_host_name_ip"),
    )

    id: int = Field(primary_key=True)
    name: str
    ip: str
