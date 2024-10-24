from sqlalchemy import Engine
from sqlmodel import create_engine, SQLModel
from os import environ


def init_engine() -> Engine:
    """
    Initialize the database engine
    :return: Engine object
    """
    print("Initializing database engine")
    return create_engine(environ.get("DATABASE_URL", "sqlite:///db.sqlite3"), echo=True)


def create_db_and_tables(engine: Engine) -> None:
    """
    Create the database and tables
    :param engine: Engine object
    :return: None
    """
    SQLModel.metadata.create_all(engine)