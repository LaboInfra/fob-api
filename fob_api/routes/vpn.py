from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from fob_api import auth
from fob_api.models.database import User
from fob_api.models.api import CreateDevice
from fob_api.tasks import headscale

router = APIRouter(prefix="/devices")

template = Jinja2Templates(directory="templates")

@router.get("/register/{mkey}", tags=["vpn"], response_class=HTMLResponse)
def register_device_get(request: Request, mkey: str):
    """
    Handle device registration for headscale require basic auth
    """
    if not mkey.startswith("mkey:"):
        raise HTTPException(status_code=400, detail="Invalid mkey")
    return template.TemplateResponse(
        request=request,
        name="register_device.html.j2",
        context={"mkey": mkey}
    )

@router.post("/register", tags=["vpn"])
async def register_device_post(request: Request):
    """
    Handle device registration for headscale require basic auth
    """
    form_data = await request.form()
    mkey = form_data.get("mkey")
    username = form_data.get("username")
    password = form_data.get("password")
    if not mkey or not username or not password:
        return template.TemplateResponse(
            request=request,
            name="register_device.html.j2",
            context={"mkey": mkey, "error": "All fields are required"}
        )
    if not mkey.startswith("mkey:"):
        return template.TemplateResponse(
            request=request,
            name="register_device.html.j2",
            context={"mkey": mkey, "error": "Invalid mkey"}
        )
    user = auth.basic_auth_validator(username, password)
    if not user:
        return template.TemplateResponse(
            request=request,
            name="register_device.html.j2",
            context={"mkey": mkey, "error": "Invalid username or password"}
        )
    
    # TODO add headscale call to validate mkey and register device

    return template.TemplateResponse(
        request=request,
        name="register_device.html.j2",
        context={"mkey": mkey, "success": "Device registered successfully you can now close this page"}
    )
