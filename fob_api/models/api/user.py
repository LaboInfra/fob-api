from pydantic import BaseModel

class Me(BaseModel):
    username: str
    email: str
    devices_access: list

class UserInfo(BaseModel):
    username: str
    email: str
    is_admin: bool
    disabled: bool

class UserCreate(BaseModel):
    username: str
    email: str

class UserResetPassword(BaseModel):
    token: str
    password: str

class UserPasswordUpdate(BaseModel):
    password: str

class UserResetPasswordResponse(BaseModel):
    message: str
