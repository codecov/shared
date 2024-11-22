# Generated by Django 4.2.16 on 2024-11-22 00:38

from django.db import migrations, models

from shared.django_apps.migration_utils import RiskyAddIndex


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0031_lastcacherollupdate_and_more"),
    ]

    operations = [
        RiskyAddIndex(
            model_name="reportsession",
            index=models.Index(
                fields=["report_id", "upload_type", "order_number"],
                name="reports_upload_order_number_upload_type_report_id_index",
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
