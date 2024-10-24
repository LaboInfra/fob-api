from datetime import datetime
from datetime import timedelta
from typing import Annotated
from fastapi import Depends, Security, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt
from jose.jwt import JWTError, ExpiredSignatureError, JWTClaimsError
from uuid import uuid4


from sqlmodel import Session, select
from fob_api.models import User
from fob_api import engine

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

http_basic_security = HTTPBasic()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
jwt_secret = "CHANGE_ME_TOTO"
jwt_issuer = "FastOnBoard-API"
jwt_expire_days = 1

def hash_password(password: str) -> str:
    """
    Hash the password using sha256
    :param password: plain text password
    :return: hashed password
    """
    return password_context.hash(password)


def encode_token(self, user_id) -> str:
    return jwt.encode({
        "exp": datetime.now() + timedelta(days=self.token_days_expiry),
        "iat": datetime.now(),
        "jti": str(uuid4()),
        "iis": self.issuer,
        "nbf": datetime.now(),
        "sub": str(user_id)
    }, self.secret, algorithm="HS256")


def decode_token(self, token: str) -> dict:
    try:
        return jwt.decode(token, self.secret, issuer=self.issuer, algorithms=["HS256"])
    except JWTClaimsError as e:
        raise HTTPException(status_code=400, detail=f"JWTClaimsError: {e}")
    except ExpiredSignatureError as e:
        raise HTTPException(status_code=400, detail=f"ExpiredSignatureError: {e}")
    except JWTError as e:
        raise HTTPException(status_code=400, detail=f"JWTError: {e}")

## Validators

### Basic Auth Validator
def basic_auth_validator(credentials: Annotated[HTTPBasicCredentials, Depends(http_basic_security)]) -> bool:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == credentials.username)).first()
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized bad username")
        if password_context.verify(credentials.password, user.password):
            raise HTTPException(status_code=401, detail="Unauthorized bad password")
        return credentials.username

### JWT Auth Validator
def jwt_auth_validator(token: Annotated[str, Depends(oauth2_scheme)]) -> bool:
    ...