# Generated by Django 4.2.13 on 2024-08-08 19:49

from django.db import migrations, models

"""
BEGIN;
--
-- Add field created_at to repository
--
ALTER TABLE "repos" ADD COLUMN "created_at" timestamp with time zone DEFAULT '2024-08-08T21:17:39.913910+00:00'::timestamptz NULL;
ALTER TABLE "repos" ALTER COLUMN "created_at" DROP DEFAULT;
COMMIT;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0056_branch_name_trgm_idx"),
    ]

    operations = [
        migrations.AddField(
            model_name="repository",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
