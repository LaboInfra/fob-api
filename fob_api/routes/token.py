from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from fob_api import auth, get_session
from fob_api.models.database import User
from fob_api.models.database import Token as TokenDB
from fob_api.models.api import Token, TokenValidate, TokenInfoID
from fob_api.managers import TokenManager

router = APIRouter()

@router.post("/token", response_model=Token, tags=["token"])
def get_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        session: Session = Depends(get_session)
    ) -> Token:
    user = auth.basic_auth_validator(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return Token(access_token=TokenManager(session).create_token(user), token_type="bearer")


@router.get("/token/refreshtoken", response_model=Token, tags=["token"])
def refresh_token(
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> Token:
    return Token(access_token=TokenManager(session).create_token(user), token_type="bearer")

@router.delete("/token/{jti}", tags=["token"])
def revoke_token(
        jti: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> None:
    # todo check if token is owned by user
    TokenManager(session).delete_token(jti)

@router.get("/token/verify", response_model=TokenValidate, tags=["token"])
def verify_token(user: Annotated[User, Depends(auth.get_current_user)]) -> TokenValidate:
    # todo user token manger
    return TokenValidate(valid=True)

@router.get("/token", tags=["token"])
def list_token(
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> list[TokenInfoID]:
    # todo check if token is owned by user
    return [TokenInfoID(
        jti=token.token_id,
        created_at=token.created_at,
        expires_at=token.expires_at,
    ) for token in TokenManager(session).list_token(user.id)]
