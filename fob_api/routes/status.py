from datetime import datetime
from typing import Sequence, Type, Annotated

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel
from sqlmodel import Session, select


router = APIRouter()

@router.get("/status/", tags=["status"])
def read_logs():
    """
    Returns global status information. TODO
    """
    return {"status": "ok", "time": datetime.now().isoformat()}