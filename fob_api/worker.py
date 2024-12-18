from celery import Celery
from fob_api import Config
from fob_api import serializer as pydantic_serializer
from kombu.serialization import register

# Register the serializer
register(
    "pydantic",
    pydantic_serializer.pydantic_dumps,
    pydantic_serializer.pydantic_loads,
    content_type="application/x-pydantic",
    content_encoding="utf-8"
)

config = Config()
celery = Celery(__name__)
celery.conf.update(
    broker_url=config.celery_broker_url,
    result_backend=config.celery_result_backend,
    broker_connection_retry_on_startup=True,
    task_serializer="pydantic",
    result_serializer="pydantic",
    event_serializer="pydantic",
    accept_content=[
        "application/json",
        "application/x-pydantic"
    ],
    result_accept_content=[
        "application/json",
        "application/x-pydantic"
    ],
    worker_pool_restarts=True,
    beat_schedule={
        'fastonboard.headscale.sync_policy': {
            'task': 'fastonboard.headscale.sync_policy',
            'schedule': 60 * 15  # every 15min
        },
    }
)
# import need to be after celery is defined to avoid circular import
from fob_api.tasks import core, headscale
