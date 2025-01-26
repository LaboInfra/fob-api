"""
Router for the API
"""
from .status import router as status_router
from .token import router as token_router
from .users import router as users_router
from .devices import router as vpn_router
from .headscale import router as headscale_router
from .openstack import router as openstack_router