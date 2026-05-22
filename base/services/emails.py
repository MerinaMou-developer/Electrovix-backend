from django.conf import settings
from django.core.mail import send_mail


def _order_items_lines(order):
    lines = []
    for item in order.orderitem_set.all():
        lines.append(f"  - {item.name} x{item.qty} @ ৳{item.price}")
    return "\n".join(lines) if lines else "  (no items)"


def send_order_confirmation_email(order_id: int) -> bool:
    from base.models import Order

    order = (
        Order.objects.select_related("user")
        .prefetch_related("orderitem_set")
        .filter(_id=order_id)
        .first()
    )
    if not order or not order.user or not order.user.email:
        return False

    if order.confirmationEmailSent:
        return True

    shipping = getattr(order, "shippingaddress", None)
    address_block = ""
    if shipping:
        address_block = (
            f"\nShip to: {shipping.address}, {shipping.city}, "
            f"{shipping.postalCode}, {shipping.country}\nPhone: {shipping.phone}"
        )

    subject = f"Electrovix — Order #{order._id} confirmed"
    body = (
        f"Hi {order.user.first_name or order.user.username},\n\n"
        f"Thank you for your order! Payment has been received.\n\n"
        f"Order ID: #{order._id}\n"
        f"Total: ৳{order.totalPrice}\n"
        f"Payment: {order.paymentMethod}\n"
        f"{address_block}\n\n"
        f"Items:\n{_order_items_lines(order)}\n\n"
        f"We will notify you when your order ships.\n\n"
        f"— Electrovix"
    )

    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        fail_silently=False,
    )
    Order.objects.filter(pk=order.pk).update(confirmationEmailSent=True)
    return True


def send_low_stock_alert_email(product_id: int) -> bool:
    from base.models import Product

    product = Product.objects.select_related("brand", "category").filter(pk=product_id).first()
    if not product:
        return False

    admin_email = settings.ADMIN_ALERT_EMAIL
    if not admin_email:
        return False

    subject = f"[Electrovix] Low stock: {product.name}"
    body = (
        f"Product: {product.name}\n"
        f"ID: {product._id}\n"
        f"Stock remaining: {product.countInStock}\n"
        f"Threshold: {settings.LOW_STOCK_THRESHOLD}\n"
        f"Brand: {product.brand.name if product.brand else '—'}\n"
        f"Category: {product.category.name if product.category else '—'}\n"
    )

    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [admin_email],
        fail_silently=False,
    )
    return True
