# Generated by Django 4.2.11 on 2024-04-12 17:04

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0015_testresultreporttotals"),
    ]

    operations = [
        migrations.AddField(
            model_name="testresultreporttotals",
            name="error",
            field=models.CharField(
                choices=[("no_success", "No Success")], max_length=100, null=True
            ),
        ),
    ]
