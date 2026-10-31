import json
from pathlib import Path
from django.db import migrations


def import_products(apps, schema_editor):
    Product = apps.get_model("website", "Product")
    records = json.loads(Path(__file__).with_name("product_seed.json").read_text(encoding="utf-8"))
    for record in records:
        Product.objects.using(schema_editor.connection.alias).get_or_create(
            name=record["name"], defaults=record,
        )


class Migration(migrations.Migration):
    dependencies = [("website", "0003_product")]
    operations = [migrations.RunPython(import_products, migrations.RunPython.noop)]
