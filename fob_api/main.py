from fastapi import FastAPI
from fob_api import Config

if not Config().validate_all():
    raise ValueError("Invalid configuration. Please check your environment variables.")

from fob_api import engine, routes

app = FastAPI(
    swagger_ui_parameters={
        "persistAuthorization": True,
    }
)

app.include_router(routes.status_router)
app.include_router(routes.token_router)
app.include_router(routes.users_router)
app.include_router(routes.vpn_router)
app.include_router(routes.headscale_router)
app.include_router(routes.openstack_router)
app.include_router(routes.quota_router)
