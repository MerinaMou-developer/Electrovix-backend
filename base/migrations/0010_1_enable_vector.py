from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("base", "0010_order_transaction_id"),
    ]

    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS vector;"),
    ]