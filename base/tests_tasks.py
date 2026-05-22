from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from base.factories import BrandFactory, CategoryFactory, ProductFactory
from base.models import Order, OrderItem, ShippingAddress
from base.services.emails import send_order_confirmation_email
from base.services.stock import decrement_stock, queue_order_confirmation


class OrderEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer@test.com",
            email="buyer@test.com",
            password="pass12345",
            first_name="Buyer",
        )
        self.category = CategoryFactory()
        self.brand = BrandFactory()
        self.product = ProductFactory(
            category=self.category,
            brand=self.brand,
            countInStock=10,
            price=Decimal("100.00"),
        )
        self.order = Order.objects.create(
            user=self.user,
            paymentMethod="SSL",
            taxPrice=Decimal("8.00"),
            shippingPrice=Decimal("10.00"),
            totalPrice=Decimal("118.00"),
            isPaid=True,
        )
        ShippingAddress.objects.create(
            order=self.order,
            address="1 Test St",
            city="Dhaka",
            postalCode="1200",
            country="BD",
            phone="01712345678",
        )
        OrderItem.objects.create(
            product=self.product,
            order=self.order,
            name=self.product.name,
            qty=1,
            price=self.product.price,
            image="/placeholder.png",
        )

    @patch("base.services.emails.send_mail")
    def test_order_confirmation_email(self, mock_send_mail):
        send_order_confirmation_email(self.order._id)
        mock_send_mail.assert_called_once()
        self.order.refresh_from_db()
        self.assertTrue(self.order.confirmationEmailSent)

    @patch("base.services.emails.send_mail")
    def test_order_confirmation_is_idempotent(self, mock_send_mail):
        send_order_confirmation_email(self.order._id)
        send_order_confirmation_email(self.order._id)
        mock_send_mail.assert_called_once()

    @patch("base.tasks.send_order_confirmation_task.apply")
    def test_queue_order_confirmation(self, mock_apply):
        queue_order_confirmation(self.order._id)
        mock_apply.assert_called_once()


@override_settings(LOW_STOCK_THRESHOLD=5, ADMIN_ALERT_EMAIL="admin@test.com")
class StockAlertTests(TestCase):
    def setUp(self):
        self.category = CategoryFactory()
        self.brand = BrandFactory()
        self.product = ProductFactory(
            category=self.category,
            brand=self.brand,
            countInStock=6,
        )

    @patch("base.services.stock.enqueue_background")
    def test_low_stock_triggers_alert(self, mock_enqueue):
        decrement_stock(self.product, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.countInStock, 4)
        mock_enqueue.assert_called_once()

    @patch("base.services.stock.enqueue_background")
    def test_stock_above_threshold_no_alert(self, mock_enqueue):
        self.product.countInStock = 20
        self.product.save()
        decrement_stock(self.product, 1)
        mock_enqueue.assert_not_called()
