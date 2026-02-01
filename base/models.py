from django.db import models
from django.contrib.auth.models import User
# Create your models here.
# Create your models here.
from django.db import models

class Brand(models.Model):
    name = models.CharField(max_length=30)
    slug = models.SlugField(max_length=40, unique=True)
    icon_class = models.CharField(max_length=50, blank=True, null=True)  # Add icon class field

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=30)
    slug = models.SlugField(max_length=40, unique=True)
    icon_class = models.CharField(max_length=50, blank=True, null=True)  # Add icon class field

    def __str__(self):
        return self.name



from django.db.models import DecimalField

from decimal import Decimal, InvalidOperation

class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    image = models.ImageField(null=True, blank=True, default='/placeholder.png')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    rating = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    numReviews = models.IntegerField(null=True, blank=True, default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discountPercentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    countInStock = models.IntegerField(null=True, blank=True, default=0)
    createdAt = models.DateTimeField(auto_now_add=True)
    _id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return self.name

    @property
    def discount_price(self):
        try:
            if self.price and self.discountPercentage is not None:
                # Ensure both price and discountPercentage are valid Decimals
                price = Decimal(self.price)
                discount = Decimal(self.discountPercentage)
                # Calculate discounted price
                return round(price - (price * discount / 100), 2)
        except InvalidOperation:
            # If there is an error in the calculation, return the original price
            return self.price
        return self.price



class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    rating = models.IntegerField(null=True, blank=True, default=0)
    comment = models.TextField(null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    _id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return str(self.rating)
    


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    paymentMethod = models.CharField(max_length=200, null=True, blank=True)
    taxPrice = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True)
    shippingPrice = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True)
    totalPrice = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True)
    isPaid = models.BooleanField(default=False)
    paidAt = models.DateTimeField(auto_now_add=False, null=True, blank=True)
    isDelivered = models.BooleanField(default=False)
    deliveredAt = models.DateTimeField(
        auto_now_add=False, null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)  # Ensure this exists
    _id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return str(self.createdAt)



class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    qty = models.IntegerField(null=True, blank=True, default=0)
    price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True)
    image = models.CharField(max_length=200, null=True, blank=True)
    _id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return str(self.name)
    

from django.core.exceptions import ValidationError
import re
from decimal import Decimal, InvalidOperation
# Custom validator for phone numbers (11 digits)
def validate_phone(value):
    phone_regex = re.compile(r'^[0-9]{11}$')  # Ensure exactly 11 digits
    if not phone_regex.match(value):
        raise ValidationError('Phone number must be exactly 11 digits.')

class ShippingAddress(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=200, null=True, blank=True)
    postalCode = models.CharField(max_length=200, null=True, blank=True)
    country = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True, validators=[validate_phone])  # Allow 11 digits phone
    shippingPrice = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    _id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return str(self.address)

    def save(self, *args, **kwargs):
        try:
            # Ensure shippingPrice is a valid Decimal
            if self.shippingPrice is not None:
                self.shippingPrice = Decimal(self.shippingPrice)
        except InvalidOperation:
            # Handle invalid Decimal value
            self.shippingPrice = Decimal('0.00')
        super(ShippingAddress, self).save(*args, **kwargs)
