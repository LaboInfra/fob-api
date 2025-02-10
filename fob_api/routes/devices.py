from typing import Annotated, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

from fob_api import auth, headscale_driver
from fob_api.lib.headscale import Node, PreAuthKey
from fob_api.models.api import DevicePreAuthKeyResponse
from fob_api.models.database import User
from fob_api.models.api import Device as ApiDeviceResponse, DeviceDeleteResponse
from fob_api.tasks import headscale as headscale_tasks

router = APIRouter(prefix="/devices")

template = Jinja2Templates(directory="templates")
MAX_ALLOWED_DEVICES = 5

def count_devices_for_user(username: str) -> int:
    return len(headscale_driver.node.list(username=username))
def can_add_device(username: str) -> bool:
    return count_devices_for_user(username) < MAX_ALLOWED_DEVICES
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

@router.post("/register/{mkey}", tags=["vpn"])
async def register_device_post(request: Request, mkey: str):
    """
    Handle device registration for headscale require basic auth
    """
    # todo add limit to max allowed devices
    form_data = await request.form()
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

    user: User = auth.basic_auth_validator(username, password)
    if not user:
        return template.TemplateResponse(
            request=request,
            name="register_device.html.j2",
            context={"mkey": mkey, "error": "Invalid username or password"}
        )

    headscale_tasks.get_or_create_user(username)

    if not can_add_device(username):
        return template.TemplateResponse(
            request=request,
            name="register_device.html.j2",
            context={"mkey": mkey, "error": f"Max allowed devices reached ({MAX_ALLOWED_DEVICES})"}
        )
    try:
        headscale_driver.node.register(username, mkey)
    except Exception as e:
        return template.TemplateResponse(
            request=request,
            name="register_device.html.j2",
            context={"mkey": mkey, "error": str(e)}
        )

    return template.TemplateResponse(
        request=request,
        name="register_device.html.j2",
        context={"mkey": mkey, "success": "Device registered successfully you can now close this page"}
    )

@router.get("/{username}", tags=["vpn"])
def list_devices(user: Annotated[User, Depends(auth.get_current_user)], username: str):
    """
    List all devices
    """
    if user.username != username and not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    nodes = headscale_driver.node.list(username=username)
    return [ApiDeviceResponse(**node.__dict__) for node in nodes]

@router.delete("/{username}/{name}", tags=["vpn"], response_model=DeviceDeleteResponse)
def delete_device(user: Annotated[User, Depends(auth.get_current_user)], username: str, name: str):
    """
    Delete a device
    """
    if user.username != username and not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not an admin")
    user_nodes: List[Node] = headscale_driver.node.list(username=username)
    for node in user_nodes:
        if node.givenName == name:
            headscale_driver.node.delete(node.id)
            return DeviceDeleteResponse(success=True, msg="Device deleted")
    return JSONResponse(status_code=404, content=DeviceDeleteResponse(success=False, msg=f"Device '{ name }' not found").model_dump())

@router.get("/{username}/preauthkey", tags=["vpn"])
def generate_preauth_key(user: Annotated[User, Depends(auth.get_current_user)], username: str):
    """
    Generate a preauth key active for 5 minutes
    """
    # todo add limit to max allowed devices
    if user.username != username:
        raise HTTPException(status_code=403, detail="You are not allowed to generate preauth key for other users")
    headscale_tasks.get_or_create_user(username=username)
    if not can_add_device(username):
        raise HTTPException(status_code=400, detail=f"Max allowed devices reached ({MAX_ALLOWED_DEVICES})")
    pre_auth_key: PreAuthKey = headscale_driver.preauthkey.create(username=username, expiration=datetime.now() + timedelta(minutes=5))
    print(pre_auth_key.__dict__)
    return DevicePreAuthKeyResponse(**pre_auth_key.__dict__)
