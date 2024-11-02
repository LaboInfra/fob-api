from os import environ

from sqlalchemy import Engine
from sqlmodel import create_engine, SQLModel


def init_engine() -> Engine:
    """
    Initialize the database engine
    :return: Engine object
    """
    print("Initializing database engine")
    database_url = environ.get("DATABASE_URL")
    if database_url is None:
        raise ValueError("DATABASE_URL environment variable is not set")
    return create_engine(database_url, echo=False)


def create_db_and_tables(engine: Engine) -> None:
    """
    Create the database and tables
    :param engine: Engine object
    :return: None
    """
    SQLModel.metadata.create_all(engine)
