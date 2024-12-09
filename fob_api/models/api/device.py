from typing import List
from pydantic import BaseModel

class CreateDevice(BaseModel):
    name: str

class Device(BaseModel):
    id: str
    ipAddresses: List[str]
    name: str
    lastSeen: str
    expiry: str
    createdAt: str
    givenName: str
    online: bool
