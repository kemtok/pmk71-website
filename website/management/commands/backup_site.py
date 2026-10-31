from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from website.backups import create_backup


class Command(BaseCommand):
    help = "Back up SQLite and media, then verify an isolated restore."

    def add_arguments(self, parser):
        parser.add_argument("--directory", default=str(settings.BASE_DIR / "backups"))

    def handle(self, *args, **options):
        try:
            path, counts = create_backup(options["directory"])
        except Exception as error:
            raise CommandError(str(error))
        self.stdout.write(self.style.SUCCESS(f"Verified backup: {path}"))
        self.stdout.write(str(counts))
