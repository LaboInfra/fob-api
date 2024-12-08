from pydantic import BaseModel

class TaskInfo(BaseModel):
    id: str
    status: str
    result: str | dict | None
