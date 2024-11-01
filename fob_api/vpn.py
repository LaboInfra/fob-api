
from os import environ
from firezone_client import FZClient

FIREZONE_ENDPOINT = environ.get('FIREZONE_ENDPOINT')
FIREZONE_TOKEN = environ.get('FIREZONE_TOKEN')

if not FIREZONE_ENDPOINT or not FIREZONE_TOKEN:
    raise Exception("Missing FIREZONE_ENDPOINT or FIREZONE_TOKEN in environment variables")

firezone_driver = FZClient(
    endpoint=environ.get('FIREZONE_ENDPOINT'),
    token=environ.get('FIREZONE_TOKEN'),
    ssl_verify=False
)
