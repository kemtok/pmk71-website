from django.db import migrations


def setup_group(apps, schema_editor):
    alias = schema_editor.connection.alias
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ct, _ = ContentType.objects.using(alias).get_or_create(app_label="website", model="orderrequest")
    group, _ = Group.objects.using(alias).get_or_create(name="Отдел продаж")
    for action in ("view", "change"):
        permission, _ = Permission.objects.using(alias).get_or_create(
            content_type=ct, codename=action + "_orderrequest",
            defaults={"name": action + " order request"})
        group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [("website", "0006_orderrequest_notification_error_and_more"),
                    ("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(setup_group, migrations.RunPython.noop)]
