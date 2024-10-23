from datetime import datetime
from typing import Sequence, Type, Annotated

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel
from sqlmodel import Session, select

from fob_api import engine, security
from fob_api.models.user import is_admin, is_valid_user

router = APIRouter()

@router.get("/status/", tags=["status"])
def read_logs(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    """
    Returns global status information. TODO
    """
    return {"status": "ok", "time": datetime.now().isoformat()}