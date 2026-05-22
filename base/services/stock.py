from django.conf import settings

from base.tasks import send_low_stock_alert_task
from base.utils.task_dispatch import enqueue_background


def decrement_stock(product, qty: int) -> None:
    """Reduce stock and queue a low-stock alert when below threshold."""
    if product.countInStock is None:
        return

    if product.countInStock < qty:
        raise ValueError(f"Not enough stock for product {product.name}")

    product.countInStock -= qty
    product.save(update_fields=["countInStock"])

    threshold = settings.LOW_STOCK_THRESHOLD
    if product.countInStock <= threshold:
        enqueue_background(send_low_stock_alert_task, product._id)


def queue_order_confirmation(order_id: int) -> None:
    from base.tasks import send_order_confirmation_task

    enqueue_background(send_order_confirmation_task, order_id)
