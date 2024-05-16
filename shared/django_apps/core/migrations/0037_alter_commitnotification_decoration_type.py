# Generated by Django 4.2.3 on 2023-10-06 16:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0036_auto_20231003_1342"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commitnotification",
            name="decoration_type",
            field=models.TextField(
                choices=[
                    ("standard", "Standard"),
                    ("upgrade", "Upgrade"),
                    ("upload_limit", "Upload Limit"),
                    ("passing_empty_upload", "Passing Empty Upload"),
                    ("failing_empty_upload", "Failing Empty Upload"),
                    ("processing_upload", "Processing Upload"),
                ],
                null=True,
            ),
        ),
        migrations.RunSQL(
            "ALTER TYPE decorations ADD VALUE IF NOT exists 'processing_upload';"
        ),
    ]
