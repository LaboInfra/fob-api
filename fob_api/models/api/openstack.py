from typing import List
from pydantic import BaseModel

class OpenStackProjectCreate(BaseModel):
    name: str

class OpenStackProject(OpenStackProjectCreate):
    id: int
    name: str
    owner: str
    members: List[str]

class OpenStackUserPassword(BaseModel):
    username: str
    password: str
