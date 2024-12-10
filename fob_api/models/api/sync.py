from pydantic import BaseModel

class SyncInfo(BaseModel):
    username: str
    firezone_account_id: str
    allowed_subnets: list[dict]
    last_synced: str
