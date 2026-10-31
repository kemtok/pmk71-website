from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a staff account with access only to sales requests."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--email", required=True)

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(username=options["username"]).exists():
            raise CommandError("Account already exists; no permissions or password were changed.")
        group = Group.objects.get(name="Отдел продаж")
        user = User(username=options["username"], email=options["email"], is_staff=True)
        password = getpass("Пароль: ")
        if password != getpass("Повторите пароль: "):
            raise CommandError("Passwords do not match.")
        try:
            validate_password(password, user=user)
        except ValidationError as error:
            raise CommandError("; ".join(error.messages))
        user.set_password(password)
        user.save()
        user.groups.add(group)
        self.stdout.write(self.style.SUCCESS("Sales account created."))
