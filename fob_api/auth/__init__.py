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
from fob_api import engine

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

http_basic_security = HTTPBasic()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
jwt_secret = Config().jwt_secret_key
jwt_expire_days = 1

if not jwt_secret:
    raise ValueError("JWT secret not set")

def hash_password(password: str) -> str:
    """
    Hash the password using sha256
    :param password: plain text password
    :return: hashed password
    """
    return password_context.hash(password)


def encode_token(username) -> str:
    return jwt.encode({
        "exp": datetime.now() + timedelta(days=jwt_expire_days),
        "iat": datetime.now(),
        "jti": str(uuid4()),
        "nbf": datetime.now(),
        "sub": str(username)
    }, jwt_secret, algorithm="HS256")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        with Session(engine) as session:
            return session.exec(select(User).where(User.username == payload["sub"])).first()
        raise HTTPException(status_code=401, detail="No user matching the token")
    except JWTClaimsError as e:
        raise HTTPException(status_code=401, detail=f"JWTClaimsError: {e}")
    except ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail=f"ExpiredSignatureError: {e}")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"JWTError: {e}")


def basic_auth_validator(username: str, password: str) -> User:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user or not password_context.verify(password, user.password):
            return False
        return user
