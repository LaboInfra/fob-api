from datetime import datetime
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenInfoID(BaseModel):
    jti: str
    expires_at: datetime
    created_at: datetime

class TokenValidate(BaseModel):
    valid: bool
