from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0011_product_embedding"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="confirmationEmailSent",
            field=models.BooleanField(default=False),
        ),
    ]
