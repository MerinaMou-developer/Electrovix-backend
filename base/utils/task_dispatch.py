import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def enqueue_background(task, *args, **kwargs):
    """
    Queue a Celery task without blocking the HTTP request.

    Important: never runs tasks inline (no task.apply) during checkout/payment,
    because SMTP or broker retries can exceed Render's gateway timeout (502).
    """
    if not getattr(settings, "CELERY_ENABLED", False):
        logger.debug("Celery disabled; skipped %s", getattr(task, "name", task))
        return None

    try:
        return task.apply_async(args=args, kwargs=kwargs)
    except Exception as exc:
        logger.warning("Failed to queue %s: %s", getattr(task, "name", task), exc)
        return None
