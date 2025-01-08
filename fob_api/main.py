from fastapi import FastAPI

from fob_api import engine, routes

app = FastAPI()

app.include_router(routes.status_router)
app.include_router(routes.token_router)
app.include_router(routes.users_router)
app.include_router(routes.vpn_router)
app.include_router(routes.headscale_router)
