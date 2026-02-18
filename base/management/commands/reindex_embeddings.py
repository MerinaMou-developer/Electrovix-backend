from django.core.management.base import BaseCommand
from sentence_transformers import SentenceTransformer
from base.models import Product

class Command(BaseCommand):
    help = "Generate embeddings for all products"

    def handle(self, *args, **options):
        model = SentenceTransformer("all-MiniLM-L6-v2")

        qs = Product.objects.select_related("category", "brand").all()
        batch_size = 64

        products = []
        texts = []

        count = 0
        for p in qs.iterator(chunk_size=500):
            products.append(p)
            texts.append(p.embedding_text())

            if len(products) >= batch_size:
                vectors = model.encode(texts, normalize_embeddings=True)
                for prod, vec in zip(products, vectors):
                    prod.embedding = vec.tolist()
                Product.objects.bulk_update(products, ["embedding"])
                count += len(products)
                self.stdout.write(f"✅ Indexed {count} products")
                products, texts = [], []

        if products:
            vectors = model.encode(texts, normalize_embeddings=True)
            for prod, vec in zip(products, vectors):
                prod.embedding = vec.tolist()
            Product.objects.bulk_update(products, ["embedding"])
            count += len(products)

        self.stdout.write(self.style.SUCCESS(f"✅ Done. Total indexed: {count}"))
