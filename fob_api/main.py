from fastapi import FastAPI

from fob_api import engine, routes
from fob_api.database import create_db_and_tables

app = FastAPI()

app.include_router(routes.status_router)
app.include_router(routes.token_router)
app.include_router(routes.users_router)


@app.on_event("startup")
def on_startup() -> None:
    """
    Create the database and tables on startup
    :return: None
    """
    create_db_and_tables(engine)
