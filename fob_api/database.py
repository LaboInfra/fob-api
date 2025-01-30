from sqlalchemy import Engine
from sqlmodel import create_engine, SQLModel
from fob_api import Config

def init_engine() -> Engine:
    """
    Initialize the database engine
    :return: Engine object
    """
    print("Initializing database engine")
    return create_engine(Config().database_url, echo=False, pool_recycle=1800, pool_pre_ping=True)
