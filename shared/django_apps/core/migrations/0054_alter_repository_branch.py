# Generated by Django 4.2.13 on 2024-07-15 14:04

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0053_increment_version"),
    ]

    operations = [
        migrations.AlterField(
            model_name="repository",
            name="branch",
            field=models.TextField(default="main"),
        ),
    ]