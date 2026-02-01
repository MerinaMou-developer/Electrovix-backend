"""
Factory Boy factories for User, Category, Brand, and Product.
Use for tests and seeding data (e.g. manage.py seed_products).
"""
import factory
from decimal import Decimal
from django.contrib.auth.models import User

from .models import Category, Brand, Product




class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_staff = False
    is_active = True
    is_superuser = False

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        password = extracted or "testpass123"
        obj.set_password(password)
        if create:
            obj.save()


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")
    icon_class = ""


class BrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Brand

    name = factory.Sequence(lambda n: f"Brand {n}")
    slug = factory.Sequence(lambda n: f"brand-{n}")
    icon_class = ""


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("paragraph")
    price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    countInStock = factory.Faker("random_int", min=0, max=100)
    rating = factory.LazyFunction(lambda: Decimal(str(round(__import__("random").uniform(3, 5), 1))))
    numReviews = factory.Faker("random_int", min=0, max=20)
    discountPercentage = None
    image = None  # or default='/placeholder.png'
    user = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
    brand = factory.SubFactory(BrandFactory)
