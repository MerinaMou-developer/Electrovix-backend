import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def enqueue(task, *args, **kwargs):
    """
    Queue a Celery task when a broker is configured; otherwise run inline.
    Safe for local dev, CI, and Render without a worker process.
    """
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        return task.apply(args=args, kwargs=kwargs)

    if not getattr(settings, "CELERY_ENABLED", False):
        return task.apply(args=args, kwargs=kwargs)

    try:
        return task.delay(*args, **kwargs)
    except Exception as exc:
        logger.warning("Celery enqueue failed, running sync: %s", exc)
        return task.apply(args=args, kwargs=kwargs)
