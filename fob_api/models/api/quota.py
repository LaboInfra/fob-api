from typing import List
from pydantic import BaseModel
from fob_api.models.database import QuotaType

class AdjustUserQuota(BaseModel):
    username: str
    type: QuotaType
    quantity: int # + for increase, - for decrease followed by a number
    comment: str | None

class AdjustUserQuotaID(AdjustUserQuota):
    id: int

class AdjustProjectQuota(BaseModel):
    username: str
    project_name: str
    type: QuotaType
    quantity: int
    comment: str | None

class AdjustProjectQuotaID(AdjustProjectQuota):
    id: int
