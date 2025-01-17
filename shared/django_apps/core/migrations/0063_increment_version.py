# Generated by Django 4.2.16 on 2025-01-15 19:54

from django.db import migrations


def update_version(apps, schema):
    Constants = apps.get_model("core", "Constants")
    version = Constants.objects.get(key="version")
    version.value = "25.1.16"
    version.save()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0062_increment_version"),
    ]

    operations = [migrations.RunPython(update_version)]
