# Generated by Django 3.2.12 on 2023-01-23 14:53

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("timeseries", "0009_auto_20220804_1305"),
    ]

    # disable real time aggregates
    # https://docs.timescale.com/timescaledb/latest/how-to-guides/continuous-aggregates/real-time-aggregates/#real-time-aggregates

    operations = [
        migrations.RunSQL(
            f"""
            alter materialized view timeseries_measurement_summary_{name} set (timescaledb.materialized_only = true);
            """,
        )
        for name in ["1day", "7day", "30day"]
        if not settings.TIMESERIES_REAL_TIME_AGGREGATES
    ]
