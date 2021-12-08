"""Celery config for Tally-HO"""
import os

from django.conf import settings
from celery import Celery


# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "tally_ho.settings.default")
app = Celery("tally_ho",
             broker=settings.CELERY_BROKER_URL,
             backend=settings.CELERY_RESULT_BACKEND)  # pylint: disable=invalid-name

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object("django.conf:settings")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(settings.INSTALLED_APPS)

@app.task
def debug_task():
    """A test task"""
    print("Hello!")
    return True