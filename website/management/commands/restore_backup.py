from django.core.management.base import BaseCommand, CommandError
from website.backups import restore_archive


class Command(BaseCommand):
    help = "Restore and verify a backup into a NEW directory; never overwrites working data."

    def add_arguments(self, parser):
        parser.add_argument("archive")
        parser.add_argument("--destination", required=True)

    def handle(self, *args, **options):
        try:
            counts = restore_archive(options["archive"], options["destination"])
        except Exception as error:
            raise CommandError(str(error))
        self.stdout.write(self.style.SUCCESS(f"Restored and verified: {counts}"))
