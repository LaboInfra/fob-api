from os import environ

from sqlalchemy import Engine
from sqlmodel import create_engine, SQLModel
from fob_api import Config

def init_engine() -> Engine:
    """
    Initialize the database engine
    :return: Engine object
    """
    print("Initializing database engine")
    return create_engine(Config().database_url, echo=False)


def create_db_and_tables(engine: Engine) -> None:
    """
    Create the database and tables
    :param engine: Engine object
    :return: None
    """
    SQLModel.metadata.create_all(engine)
