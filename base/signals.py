from django.db.models.signals import pre_save
from django.contrib.auth.models import User

from django.db.models.signals import post_save
from django.dispatch import receiver
from base.models import Product

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

