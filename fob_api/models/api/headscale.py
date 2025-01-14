from typing import List
from pydantic import BaseModel

class HeadScalePolicyAclCreate(BaseModel):
    action: str
    src: List[str]
    dst: List[str]
    proto: str | None

class HeadScalePolicyAcl(HeadScalePolicyAclCreate):
    id: int

class HeadScalePolicyHostCreate(BaseModel):
    name: str
    ip: str

class HeadScalePolicyHost(HeadScalePolicyHostCreate):
    id: int
