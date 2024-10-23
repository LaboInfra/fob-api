import hashlib

from fastapi.security import HTTPBasicCredentials
from sqlmodel import Field, SQLModel, Session, select

from fob_api import engine

class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    username: str
    password: str
    email: str
    is_admin: bool = False
    disabled: bool = False


def is_valid_user(credentials: HTTPBasicCredentials) -> bool:
    """
    Check if the user is valid by checking the credentials against the database
    :param credentials: HTTPBasicCredentials object
    :return: True if the user is valid, False otherwise
    """
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == credentials.username)).first()
        if not user:
            return False
        return verify_password(credentials.password, user.password)


def is_admin(credentials: HTTPBasicCredentials) -> bool:
    """
    Check if the user is an admin by checking the credentials against the database before checking if the user is an admin
    :param credentials: HTTPBasicCredentials object
    :return: True if the user is an admin, False otherwise
    """
    if not is_valid_user(credentials):
        return False
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == credentials.username)).first()
        if not user:
            return False
        return user.is_admin


def get_hashed_password(password: str) -> str:
    """
    Hash the password using sha256
    :param password: plain text password
    :return: hashed password
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify the plain password against the hashed password
    :param plain_password:
    :param hashed_password:
    :return: true if the plain password matches the hashed password, false otherwise
    """
    return get_hashed_password(plain_password) == hashed_password