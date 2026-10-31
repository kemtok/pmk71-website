import json
import shutil
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Restore initial photos without overwriting existing files."

    def handle(self, *args, **options):
        total = 0
        for filename in ("news_seed.json", "product_seed.json"):
            records = json.loads((settings.BASE_DIR / "website" / "migrations" / filename).read_text(encoding="utf-8"))
            for record in records:
                image = record.get("image")
                if not image:
                    continue
                rel = Path(image)
                source = settings.BASE_DIR / "assets" / rel
                target = settings.MEDIA_ROOT / rel
                if target.exists():
                    continue
                if not source.is_file():
                    raise CommandError(f"Missing initial photo: {source}")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                total += 1
        self.stdout.write(self.style.SUCCESS(f"Restored {total} photos; existing files preserved."))
