from datetime import datetime
from datetime import timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt
from jose.jwt import JWTError, ExpiredSignatureError, JWTClaimsError
from sqlmodel import Session, select

from fob_api.config import Config
from fob_api.models.database import User
from fob_api.models.database import Token as TokenDB
from fob_api import engine

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

http_basic_security = HTTPBasic()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
jwt_secret = Config().jwt_secret_key
jwt_expire_days = 15

if not jwt_secret:
    raise ValueError("JWT secret not set")

def hash_password(password: str) -> str:
    """
    Hash the password using sha256
    :param password: plain text password
    :return: hashed password
    """
    return password_context.hash(password)

def make_token_data(username: str) -> dict:
    return {
        "exp": datetime.now() + timedelta(days=jwt_expire_days),
        "iat": datetime.now(),
        "jti": str(uuid4()),
        "nbf": datetime.now(),
        "sub": str(username)
    }

def encode_token(token_data) -> str:
    return jwt.encode(token_data, jwt_secret, algorithm="HS256")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        with Session(engine) as session:
            user = session.exec(select(User).where(User.username == payload["sub"])).first()
            token = session.exec(select(TokenDB).where(TokenDB.token_id == payload["jti"])).first()
            if user and token:
                return user
        raise HTTPException(status_code=401, detail="Invalid token")
    except (JWTClaimsError, ExpiredSignatureError, JWTError) as e:
        raise HTTPException(status_code=401, detail=f"JWT Error: {e}")


def basic_auth_validator(username: str, password: str) -> User:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user or not password_context.verify(password, user.password):
            return False
        return user
