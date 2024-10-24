from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    username: str
    password: str
    email: str
    is_admin: bool = False
    disabled: bool = False
