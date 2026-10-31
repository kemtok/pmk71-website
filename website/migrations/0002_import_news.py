import json
from pathlib import Path
from django.db import migrations


def import_news(apps, schema_editor):
    News = apps.get_model("website", "News")
    records = json.loads(Path(__file__).with_name("news_seed.json").read_text(encoding="utf-8"))
    for record in records:
        News.objects.using(schema_editor.connection.alias).get_or_create(
            source_url=record["source_url"], defaults=record,
        )


class Migration(migrations.Migration):
    dependencies = [("website", "0001_initial")]
    operations = [migrations.RunPython(import_news, migrations.RunPython.noop)]
