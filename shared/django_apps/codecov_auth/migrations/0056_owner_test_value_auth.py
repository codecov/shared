# Generated by Django 4.2.11 on 2024-04-25 02:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("codecov_auth", "0055_session_login_session"),
    ]

    operations = [
        migrations.AddField(
            model_name="owner",
            name="test_value_auth",
            field=models.TextField(null=True),
        ),
    ]