from datetime import datetime, timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session, select
from celery.result import AsyncResult
from firezone_client import generate_password

from fob_api import auth, engine, TaskInfo, mail
from fob_api.models.user import User, UserPasswordReset
from fob_api.tasks.core import sync_user as task_sync_user
from fob_api.auth import hash_password
from fob_api.worker import celery

router = APIRouter(prefix="/users")

class UserInfo(BaseModel):
    username: str
    email: str
    is_admin: bool
    disabled: bool

class UserCreate(BaseModel):
    username: str
    email: str


@router.get("/", response_model=list[UserInfo], tags=["users"])
def get_users(user: Annotated[User, Depends(auth.get_current_user)]) -> list[UserInfo]:
    """
    Returns all users
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    with Session(engine) as session:
        return [item for item in session.exec(select(User))] 

@router.post("/", response_model=UserInfo, tags=["users"])
def create_user(user: Annotated[User, Depends(auth.get_current_user)], user_create: UserCreate) -> UserInfo:
    """
    Create a new user
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    with Session(engine) as session:
        # Check if user already exists
        user_exists = session.exec(select(User).where(User.email == user_create.email)).first()
        if user_exists:
            raise HTTPException(status_code=400, detail="User already exists")
        user = User(
            email=user_create.email,
            username=user_create.username,
            password=hash_password(generate_password()),
            is_admin=False,
            disabled=False
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        user_reset_password = UserPasswordReset(
            user_id=user.id,
            token=str(uuid4()),
            source_ip="",
            expires_at=datetime.now() + timedelta(days=5)
        )
        session.add(user_reset_password)
        session.commit()

        mail.send_text_mail(user.email, "LaboInfra Account Created",
            "Your LaboInfra account has been created.\n" +
            "You can reset your password by running the following command:\n"+
            f"\t`labctl reset-password --token {user_reset_password.token}`\n" +
            "This token will expire in 5 days.\n" +
            "Welcome to LaboInfra Cloud services"
        )

        return user

@router.get("/{username}", response_model=UserInfo, tags=["users"])
def get_user(user: Annotated[User, Depends(auth.get_current_user)], username: str) -> UserInfo:
    """
    Get user by username
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

@router.delete("/{username}", response_model=UserInfo, tags=["users"])
def delete_user(user: Annotated[User, Depends(auth.get_current_user)], username: str) -> UserInfo:
    """
    Delete user by username
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        session.delete(user)
        session.commit()
        return user

@router.get("/{username}/sync", response_model=TaskInfo, tags=["users"])
def sync_user(user: Annotated[User, Depends(auth.get_current_user)], username: str) -> TaskInfo:
    """
    Sync user with Firezone
    """
    if not user.is_admin or user.username != username:
        raise HTTPException(status_code=403, detail="You are not an admin")
    task = task_sync_user.delay(username)
    return TaskInfo(id=task.id, status=task.status, result=None)


@router.get("/{username}/sync/{task_id}", response_model=TaskInfo, tags=["users"])
def sync_user_status(user: Annotated[User, Depends(auth.get_current_user)], username: str, task_id: str) -> TaskInfo:
    """
    Get user sync status
    """
    if not user.is_admin or user.username != username:
        raise HTTPException(status_code=403, detail="You are not an admin")
    result = AsyncResult(task_id, app=celery)
    data = ""
    if result.status == "SUCCESS":
        data = result.get()
    return TaskInfo(id=task_id, status=result.status, result=data)
