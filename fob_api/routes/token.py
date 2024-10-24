from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel
from fob_api import auth
from fob_api.models.user import User

router = APIRouter()

@router.get("/token")
def get_token(username: Annotated[HTTPBasicCredentials, Depends(auth.basic_auth_validator)]) -> str:
    """
    Get a JWT token
    :param credentials: HTTPBasicCredentials object
    :return: JWT token
    """
    return auth.JWTAuthHandler().encode_token(username)

@router.get("/token/decode")
def decode_token(token: Annotated[str, Depends(auth.jwt_auth_validator)]) -> dict:
    """
    Decode a JWT token
    :param token: JWT token
    :return: decoded token
    """
    return auth.JWTAuthHandler().decode_token(token)