from celery import Celery
from fob_api import Config

config = Config()
celery = Celery(__name__)
celery.conf.update(
    broker_url=config.celery_broker_url,
    result_backend=config.celery_result_backend,
    broker_connection_retry_on_startup=True
)
# import need to be after celery is defined to avoid circular import
from fob_api.tasks import core
