from firezone_client import FZClient
from fob_api import Config

config = Config()

firezone_driver = FZClient(
    endpoint=config.firezone_endpoint,
    token=config.firezone_token,
    ssl_verify=False
)
