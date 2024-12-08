from pydantic import BaseModel

class CreateDevice(BaseModel):
    name: str