"""
Seed categories, brands, users, and products using Factory Boy.
Products data matches frontend products.js (Electronics, Apple, Sony, etc.).
Run: python manage.py seed_products
Optional: python manage.py seed_products --clear  (delete existing products/categories/brands from base app)
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from base.models import Category, Brand, Product
from base.factories import UserFactory, CategoryFactory, BrandFactory, ProductFactory


# Product data from frontend products.js (name, brand, category, price, etc.)
PRODUCTS_DATA = [
    {
        "name": "Airpods Wireless Bluetooth Headphones",
        "image": "/images/airpods.jpg",
        "description": "Bluetooth technology lets you connect it with compatible devices wirelessly High-quality AAC audio offers immersive listening experience Built-in microphone allows you to take calls while working",
        "brand": "Apple",
        "category": "Electronics",
        "price": Decimal("89.99"),
        "countInStock": 10,
        "rating": Decimal("4.5"),
        "numReviews": 12,
    },
    {
        "name": "iPhone 11 Pro 256GB Memory",
        "image": "/images/phone.jpg",
        "description": "Introducing the iPhone 11 Pro. A transformative triple-camera system that adds tons of capability without complexity. An unprecedented leap in battery life",
        "brand": "Apple",
        "category": "Electronics",
        "price": Decimal("599.99"),
        "countInStock": 0,
        "rating": Decimal("4.0"),
        "numReviews": 8,
    },
    {
        "name": "Cannon EOS 80D DSLR Camera",
        "image": "/images/camera.jpg",
        "description": "Characterized by versatile imaging specs, the Canon EOS 80D further clarifies itself using a pair of robust focusing systems and an intuitive design",
        "brand": "Cannon",
        "category": "Electronics",
        "price": Decimal("929.99"),
        "countInStock": 5,
        "rating": Decimal("3"),
        "numReviews": 12,
    },
    {
        "name": "Sony Playstation 4 Pro White Version",
        "image": "/images/playstation.jpg",
        "description": "The ultimate home entertainment center starts with PlayStation. Whether you are into gaming, HD movies, television, music",
        "brand": "Sony",
        "category": "Electronics",
        "price": Decimal("399.99"),
        "countInStock": 11,
        "rating": Decimal("5"),
        "numReviews": 12,
    },
    {
        "name": "Logitech G-Series Gaming Mouse",
        "image": "/images/mouse.jpg",
        "description": "Get a better handle on your games with this Logitech LIGHTSYNC gaming mouse. The six programmable buttons allow customization for a smooth playing experience",
        "brand": "Logitech",
        "category": "Electronics",
        "price": Decimal("49.99"),
        "countInStock": 7,
        "rating": Decimal("3.5"),
        "numReviews": 10,
    },
    {
        "name": "Amazon Echo Dot 3rd Generation",
        "image": "/images/alexa.jpg",
        "description": "Meet Echo Dot - Our most popular smart speaker with a fabric design. It is our most compact smart speaker that fits perfectly into small space",
        "brand": "Amazon",
        "category": "Electronics",
        "price": Decimal("29.99"),
        "countInStock": 0,
        "rating": Decimal("4"),
        "numReviews": 12,
    },
]


# ---- EXTRA PRODUCTS for Semantic Search testing (Gaming Laptop etc.) ----
PRODUCTS_DATA += [
    {
        "name": "ASUS ROG Strix G15 Gaming Laptop",
        "image": "/images/laptop-asus-rog.jpg",
        "description": "15.6-inch gaming laptop with high refresh display, powerful GPU, fast SSD, great for gaming and heavy tasks.",
        "brand": "ASUS",
        "category": "Laptops",
        "price": Decimal("1199.99"),
        "countInStock": 6,
        "rating": Decimal("4.6"),
        "numReviews": 18,
    },
    {
        "name": "Lenovo Legion 5 Gaming Laptop",
        "image": "/images/laptop-lenovo-legion.jpg",
        "description": "Lenovo Legion gaming laptop with strong performance, good cooling, and smooth gameplay experience.",
        "brand": "Lenovo",
        "category": "Laptops",
        "price": Decimal("1099.99"),
        "countInStock": 8,
        "rating": Decimal("4.5"),
        "numReviews": 22,
    },
    {
        "name": "Acer Nitro 5 Gaming Laptop",
        "image": "/images/laptop-acer-nitro.jpg",
        "description": "Budget gaming laptop, solid FPS for popular games, SSD storage, and good value for money.",
        "brand": "Acer",
        "category": "Laptops",
        "price": Decimal("899.99"),
        "countInStock": 10,
        "rating": Decimal("4.2"),
        "numReviews": 30,
    },
    {
        "name": "Dell XPS 13 Ultrabook Laptop",
        "image": "/images/laptop-dell-xps.jpg",
        "description": "Premium ultrabook with sharp display, lightweight design, fast performance for office and study.",
        "brand": "Dell",
        "category": "Laptops",
        "price": Decimal("1299.99"),
        "countInStock": 5,
        "rating": Decimal("4.7"),
        "numReviews": 15,
    },
    {
        "name": "Apple MacBook Air M2",
        "image": "/images/laptop-macbook-air.jpg",
        "description": "Thin and light laptop with great battery life and smooth performance for coding, design, and everyday work.",
        "brand": "Apple",
        "category": "Laptops",
        "price": Decimal("999.99"),
        "countInStock": 7,
        "rating": Decimal("4.8"),
        "numReviews": 40,
    },
    {
        "name": "Logitech G Pro Wireless Gaming Mouse",
        "image": "/images/mouse-logitech-gpro.jpg",
        "description": "Esports-grade wireless gaming mouse, ultra-lightweight, accurate sensor, perfect for FPS games.",
        "brand": "Logitech",
        "category": "Gaming Accessories",
        "price": Decimal("129.99"),
        "countInStock": 12,
        "rating": Decimal("4.7"),
        "numReviews": 50,
    },
]


def slugify(name):
    return name.lower().replace(" ", "-").replace("'", "")[:40]


class Command(BaseCommand):
    help = "Seed categories, brands, a demo user, and products (from products.js data) using Factory Boy."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing Products, Categories, and Brands (from base app) before seeding.",
        )
        parser.add_argument(
            "--users",
            type=int,
            default=1,
            help="Number of extra users to create with UserFactory (default: 1).",
        )

    def handle(self, *args, **options):
        clear = options["clear"]
        extra_users = options["users"]

        if clear:
            self.stdout.write("Clearing existing Products, Categories, Brands...")
            Product.objects.all().delete()
            Category.objects.all().delete()
            Brand.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared."))

        # Get or create categories and brands by name (from products.js)
        categories_by_name = {}
        brands_by_name = {}

        for cat_name in {p["category"] for p in PRODUCTS_DATA}:
            slug = slugify(cat_name)
            cat, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={"name": cat_name, "icon_class": ""},
            )
            categories_by_name[cat_name] = cat

        for brand_name in {p["brand"] for p in PRODUCTS_DATA}:
            slug = slugify(brand_name)
            brand, _ = Brand.objects.get_or_create(
                slug=slug,
                defaults={"name": brand_name, "icon_class": ""},
            )
            brands_by_name[brand_name] = brand

        # Create or reuse demo user (handles both "demouser" and legacy "demo@example.com")
        demo_user = (
            User.objects.filter(username="demouser").first()
            or User.objects.filter(username="demo@example.com").first()
        )
        if demo_user:
            self.stdout.write(
                self.style.SUCCESS(f"Using existing demo user: {demo_user.username}")
            )
        else:
            demo_user = User.objects.create_user(
                username="demouser",
                email="demo@example.com",
                password="demo123",
            )
            self.stdout.write(self.style.SUCCESS("Created demo user: demouser / demo123"))
        for i in range(extra_users - 1):
            UserFactory()

        # Create products using Factory Boy with products.js data
        created = 0
        for data in PRODUCTS_DATA:
            product, was_created = Product.objects.get_or_create(
                name=data["name"],
                defaults={
                    "user": demo_user,
                    "category": categories_by_name[data["category"]],
                    "brand": brands_by_name[data["brand"]],
                    "description": data["description"],
                    "image": data.get("image") or "/placeholder.png",
                    "price": data["price"],
                    "countInStock": data["countInStock"],
                    "rating": data["rating"],
                    "numReviews": data["numReviews"],
                },
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeding complete. Categories: {len(categories_by_name)}, "
                f"Brands: {len(brands_by_name)}, Products created: {created}."
            )
        )