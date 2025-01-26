from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from fob_api import auth
from fob_api.models.database import User
from fob_api.models.api import Token, TokenValidate

router = APIRouter()

@router.post("/token", response_model=Token, tags=["token"])
def get_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> str:
    user = auth.basic_auth_validator(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth.encode_token(user.username)
    return Token(access_token=token, token_type="bearer")


@router.get("/token/refreshtoken", response_model=Token, tags=["token"])
def refresh_token(user: Annotated[User, Depends(auth.get_current_user)]) -> str:
    token = auth.encode_token(user.username)
    return Token(access_token=token, token_type="bearer")

@router.get("/token/verify", response_model=TokenValidate, tags=["token"])
def verify_token(user: Annotated[User, Depends(auth.get_current_user)]) -> str:
    return TokenValidate(valid=True)
