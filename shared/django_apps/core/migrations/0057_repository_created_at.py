# Generated by Django 4.2.13 on 2024-08-08 19:49

from django.db import migrations

"""
BEGIN;
--
-- Raw SQL operation
--
ALTER TABLE "repos" ADD COLUMN "created_at" timestamp with time zone DEFAULT null NULL;
COMMIT;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0056_branch_name_trgm_idx"),
    ]

    operations = [
        migrations.RunSQL(
            'ALTER TABLE "repos" ADD COLUMN "created_at" timestamp with time zone DEFAULT null NULL;'
        ),
    ]
