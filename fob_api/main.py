from fastapi import FastAPI

from . import engine, routes
from .database import create_db_and_tables


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


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint
    This route is useless, I just leave it here because I don't care about it :)
    :return: dict[str, str] Hello World
    """
    from fob_api.worker import create_test_task
    create_test_task.delay()
    return {"message": "Hello World"}