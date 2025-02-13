from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from fob_api import auth, get_session
from fob_api.models.database import User
from fob_api.models.database import Token as TokenDB
from fob_api.models.api import Token, TokenValidate

router = APIRouter()

@router.post("/token", response_model=Token, tags=["token"])
def get_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        session: Session = Depends(get_session)
    ) -> Token:
    user = auth.basic_auth_validator(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token_data = auth.make_token_data(user.username)
    token_db: TokenDB = TokenDB(
        expires_at=token_data["exp"],
        created_at=token_data["iat"],
        token_id=token_data["jti"],
        user_id=user.id,
    )
    session.add(token_db)
    session.commit()
    token = auth.encode_token(token_data)
    return Token(access_token=token, token_type="bearer")


@router.get("/token/refreshtoken", response_model=Token, tags=["token"])
def refresh_token(
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> Token:
    token_data = auth.make_token_data(user.username)
    token_db: TokenDB = TokenDB(
        expires_at=token_data["exp"],
        created_at=token_data["iat"],
        token_id=token_data["jti"],
        user_id=user.id,
    )
    session.add(token_db)
    session.commit()
    token = auth.encode_token(token_data)
    return Token(access_token=token, token_type="bearer")

@router.delete("/token/{jti}", tags=["token"])
def revoke_token(
        jti: str,
        user: Annotated[User, Depends(auth.get_current_user)],
        session: Session = Depends(get_session)
    ) -> None:
    token = session.exec(select(TokenDB).where(TokenDB.token_id == jti)).first()
    if not token or token.user_id != user.id:
        raise HTTPException(status_code=404, detail="Cant revoke token")
    session.delete(token)
    session.commit()

@router.get("/token/verify", response_model=TokenValidate, tags=["token"])
def verify_token(user: Annotated[User, Depends(auth.get_current_user)]) -> TokenValidate:
    return TokenValidate(valid=True)
