from sqlmodel import Session, create_engine
from sqlalchemy import Engine
from fob_api import Config


def init_engine() -> Engine:
    """
    Initialize the database engine
    :return: Engine object
    """
    print("Initializing database engine")
    return create_engine(
        Config().database_url,
        echo=False,
        pool_recycle=1800,
        pool_pre_ping=True
    )


engine = init_engine()


def get_session():
    with Session(engine) as session:
        return session
