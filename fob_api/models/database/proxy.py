from datetime import datetime
from sqlmodel import Field, SQLModel

class ProxyServiceMapCreate(SQLModel):
    project_id: int = Field(foreign_key="openstack_project.id", nullable=False)
    rule: str = Field() # for the moment rule mapp to  Host(``)
    target: str = Field() # split by comma, e.g. "http://example1.com,https://example2.com"

class ProxyServiceMap(ProxyServiceMapCreate, table=True):
    """
    Represents one quota adjustment for a user
    """
    __tablename__ = "proxy_service_map"

    id: int = Field(primary_key=True)
    created_at: datetime = Field(default=datetime.now())
    latest_dns_check: datetime = Field(default=None, nullable=True)  # Last DNS check timestamp
    latest_dns_check_result: bool = Field(default=None, nullable=True)  # Result of the last DNS check (True/False)

class ProxyServiceMapPublic(ProxyServiceMapCreate):
    """
    Represents a public view of the ProxyServiceMap, excluding sensitive fields.
    """
    id: int
    created_at: datetime = Field(default=datetime.now())