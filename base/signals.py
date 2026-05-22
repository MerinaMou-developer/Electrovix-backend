from django.db.models.signals import pre_save, post_save, post_delete
from django.contrib.auth.models import User

from django.dispatch import receiver
from base.models import Product, Category, Brand
from base.utils.catalog_cache import invalidate_catalog_cache

def updateUser(sender, instance, **kwargs):
    user = instance
    if user.email != '':
        user.username = user.email


pre_save.connect(updateUser, sender=User)



from base.ai.embedding import embed_text

@receiver(post_save, sender=Product)
def update_product_embedding(sender, instance, **kwargs):
    text = instance.embedding_text()
    vector = embed_text(text)
    Product.objects.filter(pk=instance.pk).update(embedding=vector)


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
@receiver(post_save, sender=Brand)
@receiver(post_delete, sender=Brand)
def bust_catalog_cache(sender, **kwargs):
    invalidate_catalog_cache()

