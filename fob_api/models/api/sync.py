from pydantic import BaseModel

class SyncInfo(BaseModel):
    username: str
    last_synced: str
