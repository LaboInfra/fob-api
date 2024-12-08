from sqlmodel import Session, select
from uuid import UUID

from fob_api.models.user import User
from fob_api.worker import celery
from fob_api import engine, headscale_driver

def create_user(username: str):
    """
    Create User namescpaces in HeadScale Controller

    Returns: HeadScale User object
    """
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise Exception("User not found")
        try:
            return headscale_driver.user.get(name=user.username)
        except Exception:
            print(f"User {user.email} not found in HeadScale VPN, creating...")
            headscale_driver.user.create(name=user.username)
            return create_user(username)
