from datetime import datetime, timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from celery.result import AsyncResult

from fob_api import auth, engine, mail
from fob_api import Config
from fob_api.models.api import TaskInfo, SyncInfo
from fob_api.models.database import User, UserPasswordReset
from fob_api.models.api import UserCreate, UserInfo, UserResetPassword, UserPasswordUpdate, UserResetPasswordResponse, UserMeshGroup
from fob_api.models.database import HeadScalePolicyGroupMember
from fob_api.tasks.core import sync_user as task_sync_user
from fob_api.auth import hash_password
from fob_api.worker import celery

router = APIRouter(prefix="/users")

@router.get("/", response_model=list[UserInfo], tags=["users", "admin"])
def get_users(user: Annotated[User, Depends(auth.get_current_user)]) -> list[UserInfo]:
    """
    Returns all users
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    with Session(engine) as session:
        return [item for item in session.exec(select(User))] 

@router.post("/", response_model=UserInfo, tags=["users", "admin"])
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
            password=hash_password(str(uuid4())),
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
        

        try:
            mail.send_text_mail(user.email, "LaboInfra Account Created",
                "Your LaboInfra account has been created.\n" +
                "You can reset your password by running the following command:\n"+
                f"\t`labctl reset-password --username {user.username} --token {user_reset_password.token}`\n" +
                "This token will expire in 5 days.\n" +
                "Welcome to LaboInfra Cloud services"
            )
        except mail.SMTPRecipientsRefused:
            print("Failed to send email, deleting user")
            session.delete(user)
        except ConnectionRefusedError:
            config = Config()
            print(f"Failed to connect to mail server, leaving user in database ({config.mail_server}:{config.mail_port})")
        
        session.commit()
        return UserInfo(
            username=user.username,
            email=user.email,
            is_admin=user.is_admin,
            disabled=user.disabled
        )

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
    Sync user with to external services
    """
    if user.username != username and not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    task = task_sync_user.delay(username)
    return TaskInfo(id=task.id, status=task.status, result=None)


@router.get("/{username}/sync/{task_id}", response_model=TaskInfo, tags=["users"])
def sync_user_status(user: Annotated[User, Depends(auth.get_current_user)], username: str, task_id: str) -> TaskInfo:
    """
    Get user sync status
    """
    if user.username != username and not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    result = AsyncResult(task_id, app=celery)
    data = ""
    if result.status == "SUCCESS":
        data: SyncInfo = result.get().model_dump()
    return TaskInfo(id=task_id, status=result.status, result=data)

@router.post("/{username}/reset-password", response_model=UserResetPasswordResponse, tags=["users"])
def reset_password(username: str, user_reset_password: UserResetPassword) -> UserResetPasswordResponse:
    """
    Reset user password
    """
    # Todo add rate limiting and source_ip validation to prevent abuse
    with Session(engine) as session:
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
        if len(password) < 12:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
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
def change_password(user: Annotated[User, Depends(auth.get_current_user)], username: str, user_password_update: UserPasswordUpdate) -> UserResetPasswordResponse:
    """
    Change user password
    """
    if user.username != username and not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="Unable to change password")
        password = user_password_update.password
        user.password = hash_password(password)
        session.add(user)
        session.commit()
        return UserResetPasswordResponse(message="Password changed successfully")

@router.get("/{username}/vpn-group", response_model=UserMeshGroup, tags=["users"])
def get_user_vpn_group(user: Annotated[User, Depends(auth.get_current_user)], username: str) -> UserMeshGroup:
    """
    Get user vpn group
    """
    if user.username != username and not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        groups = session.exec(select(HeadScalePolicyGroupMember).where(HeadScalePolicyGroupMember.member == user.username))
        return UserMeshGroup(username=user.username, groups=[group.name for group in groups])

@router.post("/{username}/vpn-group/{group_name}", response_model=UserMeshGroup, tags=["users", "admin"])
def add_user_vpn_group(user: Annotated[User, Depends(auth.get_current_user)], username: str, group_name: str) -> UserMeshGroup:
    """
    Add user to vpn group
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    with Session(engine) as session:
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

@router.delete("/{username}/vpn-group/{group_name}", response_model=UserMeshGroup, tags=["users", "admin"])
def delete_user_vpn_group(user: Annotated[User, Depends(auth.get_current_user)], username: str, group_name: str) -> UserMeshGroup:
    """
    Remove user from vpn group
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    with Session(engine) as session:
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
def forgot_password(email: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            raise HTTPException(status_code=418, detail="If you are a teapot, I am a coffee pot")
        user_reset_password = UserPasswordReset(
            user_id=user.id,
            token=str(uuid4()),
            source_ip="",
            expires_at=datetime.now() + timedelta(minutes=5)
        )
        session.add(user_reset_password)
        session.commit()
        try:
            mail.send_text_mail(user.email, "LaboInfra Password Reset",
                "You have requested a password reset for your LaboInfra account.\n" +
                "You can reset your password by running the following command:\n"+
                f"\t`labctl reset-password --username {user.username} --token {user_reset_password.token}`\n" +
                "This token will expire in 5 minutes.\n" +
                "If you did not request this, please ignore this email."
            )
        except mail.SMTPRecipientsRefused:
            print("Failed to send email, deleting user")
            session.delete(user)
            session.commit()
            
    raise HTTPException(status_code=418, detail="If you are a teapot, I am a coffee pot")
