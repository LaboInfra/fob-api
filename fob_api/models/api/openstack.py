from typing import List
from pydantic import BaseModel

class OpenStackProjectCreate(BaseModel):
    name: str

class OpenStackProject(OpenStackProjectCreate):
    id: int
