from datetime import datetime, timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from celery.result import AsyncResult

from fob_api import auth, engine, mail, get_session
from fob_api import Config
from fob_api.models.api import TaskInfo, SyncInfo
from fob_api.models.database import User, UserPasswordReset
from fob_api.models.api import UserCreate, UserInfo, UserResetPassword, UserPasswordUpdate, UserResetPasswordResponse, UserMeshGroup
from fob_api.models.database import HeadScalePolicyGroupMember
from fob_api.tasks.core import sync_user as task_sync_user
from fob_api.auth import hash_password
from fob_api.worker import celery

router = APIRouter(prefix="/users")

@router.get("/", response_model=list[UserInfo], tags=["users"])
def get_users(
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> list[UserInfo]:
    """
    Returns all users
    """
    auth.is_admin(user)
    return [item for item in session.exec(select(User))]

@router.post("/", response_model=UserInfo, tags=["users"])
def create_user(
        user_create: UserCreate,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> UserInfo:
    """
    Create a new user
    """
    auth.is_admin(user)
    # Check if user already exists
    user_exists = session.exec(select(User).where(User.email == user_create.email)).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="User already exists")
    new_user = User(
        email=user_create.email,
        username=user_create.username,
        password=hash_password(str(uuid4())),
        is_admin=False,
        disabled=False
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    TIME_DAY_DELTA = 5

    user_reset_password = UserPasswordReset(
        user_id=new_user.id,
        token=str(uuid4()),
        source_ip="",
        expires_at=datetime.now() + timedelta(days=TIME_DAY_DELTA)
    )
    session.add(user_reset_password)

    try:
        mail.send_mail(new_user.email, 'Your LaboInfra account has been created.', 'account_created.html.j2', {
            "username": new_user.username,
            "token": user_reset_password.token,
            "expire_time": str(TIME_DAY_DELTA) + " days"
        })
    except mail.SMTPRecipientsRefused:
        print("Failed to send email, deleting user")
        session.delete(new_user)
    except ConnectionRefusedError:
        config = Config()
        print(f"Failed to connect to mail server, leaving user in database ({config.mail_server}:{config.mail_port})")
    
    session.commit()

    task_sync_user.delay(new_user.username)

    return UserInfo(
        username=new_user.username,
        email=new_user.email,
        is_admin=new_user.is_admin,
        disabled=new_user.disabled
    )

@router.get("/{username}", response_model=UserInfo, tags=["users"])
def get_user(
        username: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> UserInfo:
    """
    Get user by username
    """
    auth.is_admin(user)
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{username}", response_model=UserInfo, tags=["users"])
def delete_user(
        username: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> UserInfo:
    """
    Delete user by username
    """
    auth.is_admin(user)
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(user)
    session.commit()
    return user

@router.get("/{username}/sync", response_model=TaskInfo, tags=["users"])
def sync_user(
        username: str,
        user: Annotated[User, Depends(auth.get_current_user)],
    ) -> TaskInfo:
    """
    Sync user with to external services
    """
    auth.is_admin_or_self(user, username)
    task = task_sync_user.delay(username)
    return TaskInfo(id=task.id, status=task.status, result=None)


@router.get("/{username}/sync/{task_id}", response_model=TaskInfo, tags=["users"])
def sync_user_status(
        username: str,
        task_id: str,
        user: Annotated[User, Depends(auth.get_current_user)]
    ) -> TaskInfo:
    """
    Get user sync status
    """
    auth.is_admin_or_self(user, username)
    result = AsyncResult(task_id, app=celery)
    data = ""
    if result.status == "SUCCESS":
        data: SyncInfo = result.get().model_dump()
    return TaskInfo(id=task_id, status=result.status, result=data)

@router.post("/{username}/reset-password", response_model=UserResetPasswordResponse, tags=["users"])
def reset_password(
        username: str,
        user_reset_password: UserResetPassword,
        session: Session = Depends(get_session)
    ) -> UserResetPasswordResponse:
    """
    Reset user password
    """
    # Todo add rate limiting and source_ip validation to prevent abuse
    user = session.exec(select(User).where(User.username == username)).first()
    password = user_reset_password.password
    if not user:
        raise HTTPException(status_code=404, detail="Unable to reset password")
    user_reset_password: UserPasswordReset = session.exec(
        select(UserPasswordReset)
        .where(UserPasswordReset.token == user_reset_password.token)
        .where(UserPasswordReset.user_id == user.id)
    ).first()
    if not user_reset_password:
        raise HTTPException(status_code=404, detail="Unable to reset password")
    if user_reset_password.expires_at < datetime.now():
        session.delete(user_reset_password)
        session.commit()
        raise HTTPException(status_code=404, detail="Unable to reset password")
    # Check password strength (i know this is not the best way to do but i am lazy :p )
    if len(password) <= 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters long")
    if not any(char.isdigit() for char in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one digit")
    if not any(char.isupper() for char in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not any(char.islower() for char in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
    if not any(char in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for char in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character")
    user.password = hash_password(password)
    session.delete(user_reset_password)
    session.commit()
    return UserResetPasswordResponse(message="Password reset successfully")

@router.post("/{username}/change-password", response_model=UserResetPasswordResponse, tags=["users"])
def change_password(
        username: str,
        user_password_update: UserPasswordUpdate,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> UserResetPasswordResponse:
    """
    Change user password
    """
    auth.is_admin_or_self(user, username)
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Unable to change password")
    password = user_password_update.password
    user.password = hash_password(password)
    session.add(user)
    session.commit()
    return UserResetPasswordResponse(message="Password changed successfully")

@router.get("/{username}/vpn-group", response_model=UserMeshGroup, tags=["users"])
def get_user_vpn_group(
        username: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> UserMeshGroup:
    """
    Get user vpn group
    """
    auth.is_admin_or_self(user, username)
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    groups = session.exec(select(HeadScalePolicyGroupMember).where(HeadScalePolicyGroupMember.member == user.username))
    return UserMeshGroup(username=user.username, groups=[group.name for group in groups])

@router.post("/{username}/vpn-group/{group_name}", response_model=UserMeshGroup, tags=["users"])
def add_user_vpn_group(
        username: str,
        group_name: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> UserMeshGroup:
    """
    Add user to vpn group
    """
    auth.is_admin(user)
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Check if user is already in group
    group_member = session.exec(
        select(HeadScalePolicyGroupMember)
        .where(HeadScalePolicyGroupMember.name == group_name)
        .where(HeadScalePolicyGroupMember.member == username)
    ).first()
    if group_member:
        raise HTTPException(status_code=400, detail="User is already in group")
    # Add user to group
    group_member = HeadScalePolicyGroupMember(name=group_name, member=username)
    session.add(group_member)
    session.commit()
    new_group = session.exec(select(HeadScalePolicyGroupMember).where(HeadScalePolicyGroupMember.member == username))
    return UserMeshGroup(username=username, groups=[group.name for group in new_group])

@router.delete("/{username}/vpn-group/{group_name}", response_model=UserMeshGroup, tags=["users"])
def delete_user_vpn_group(
        username: str,
        group_name: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> UserMeshGroup:
    """
    Remove user from vpn group
    """
    auth.is_admin(user)
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Check if user is in group
    group_member = session.exec(
        select(HeadScalePolicyGroupMember)
        .where(HeadScalePolicyGroupMember.name == group_name)
        .where(HeadScalePolicyGroupMember.member == username)
    ).first()
    if not group_member:
        raise HTTPException(status_code=404, detail="User is not in group")
    session.delete(group_member)
    session.commit()
    new_group = session.exec(select(HeadScalePolicyGroupMember).where(HeadScalePolicyGroupMember.member == username))
    return UserMeshGroup(username=username, groups=[group.name for group in new_group])

@router.post("/forgot-password", response_model=None, tags=["users"])
def forgot_password(
        email: str,
        session: Session = Depends(get_session)
    ) -> None:
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=418, detail="If you are a teapot, I am a coffee pot")
    TIME_DELTA = 5
    user_reset_password = UserPasswordReset(
        user_id=user.id,
        token=str(uuid4()),
        source_ip="",
        expires_at=datetime.now() + timedelta(minutes=TIME_DELTA)
    )
    session.add(user_reset_password)
    session.commit()
    try:
        mail.send_mail(user.email, 'LaboInfra Password Reset', 'account_password_reset.html.j2', {
            "username": user.username,
            "token": user_reset_password.token,
            "expire_time": str(TIME_DELTA) + " minutes"
        })
    except mail.SMTPRecipientsRefused:
        print("Failed to send email, deleting user")
        session.delete(user)
        session.commit()

    raise HTTPException(status_code=418, detail="If you are a teapot, I am a coffee pot")
