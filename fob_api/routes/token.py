from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from fob_api import auth
from fob_api.models.user import User

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/token", response_model=Token, tags=["token"])
def get_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> str:
    user = auth.basic_auth_validator(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth.encode_token(user.username)
    return Token(access_token=token, token_type="bearer")

@router.get("/token/me", tags=["token"])
def get_me(user: Annotated[User, Depends(auth.get_current_user)]) -> str:
    return user.username

@router.get("/token/refreshtoken", response_model=Token, tags=["token"])
def refresh_token(user: Annotated[User, Depends(auth.get_current_user)]) -> str:
    token = auth.encode_token(user.username)
    return Token(access_token=token, token_type="bearer")
