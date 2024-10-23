from fastapi import FastAPI

#from . import engine, views
#from .database import create_db_and_tables


app = FastAPI()

#app.include_router(views.log_router)
#app.include_router(views.user_router)


@app.on_event("startup")
def on_startup() -> None:
    """
    Create the database and tables on startup
    :return: None
    """
    ... #create_db_and_tables(engine)


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint
    This route is useless, I just leave it here because I don't care about it :)
    :return: dict[str, str] Hello World
    """
    return {"message": "Hello World"}