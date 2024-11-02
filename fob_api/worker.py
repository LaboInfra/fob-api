import os
import time

from celery import Celery

celery = Celery(__name__)
celery.conf.update(
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379'),
    broker_connection_retry_on_startup=True
)
# import need to be after celery is defined to avoid circular import
from fob_api.tasks import firezone
from fob_api.tasks import core
