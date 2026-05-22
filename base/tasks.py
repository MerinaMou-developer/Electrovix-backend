import logging

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from base.services.emails import (
    send_low_stock_alert_email,
    send_order_confirmation_email,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation_task(self, order_id: int):
    try:
        send_order_confirmation_email(order_id)
    except Exception as exc:
        logger.exception("Order confirmation email failed for order %s", order_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_low_stock_alert_task(self, product_id: int):
    alert_key = f"stock_alert:sent:{product_id}"
    if cache.get(alert_key):
        return

    try:
        if send_low_stock_alert_email(product_id):
            cache.set(alert_key, 1, settings.LOW_STOCK_ALERT_COOLDOWN)
    except Exception as exc:
        logger.exception("Low stock alert failed for product %s", product_id)
        raise self.retry(exc=exc)
