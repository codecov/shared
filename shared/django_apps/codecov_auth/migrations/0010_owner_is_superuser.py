# Generated by Django 3.1.13 on 2022-05-24 16:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("codecov_auth", "0009_auto_20220511_1313"),
    ]

    operations = [
        migrations.AddField(
            model_name="owner",
            name="is_superuser",
            field=models.BooleanField(null=True),
        ),
    ]
