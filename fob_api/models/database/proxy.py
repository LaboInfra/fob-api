from datetime import datetime
from sqlmodel import Field, SQLModel, Column

class ProxyServiceMap(SQLModel, table=True):
    """
    Represents one quota adjustment for a user
    """
    __tablename__ = "proxy_service_map"

    id: int = Field(primary_key=True)
    project_id: int = Field(foreign_key="openstack_project.id", nullable=False)
    rule: str = Field() # for the moment rule mapp to  Host(``)
    target: str = Field() # split by comma, e.g. "http://example1.com,https://example2.com"
    created_at: datetime = Field(default=datetime.now())
