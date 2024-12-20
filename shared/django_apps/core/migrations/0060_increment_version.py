# Generated by Django 4.2.16 on 2024-12-02 19:52

from django.db import migrations


def update_version(apps, schema):
    Constants = apps.get_model("core", "Constants")
    version = Constants.objects.get(key="version")
    version.value = "24.12.2"
    version.save()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0059_increment_version"),
    ]

    operations = [
        migrations.RunPython(
            code=update_version,
            reverse_code=migrations.RunPython.noop,
        )
    ]
