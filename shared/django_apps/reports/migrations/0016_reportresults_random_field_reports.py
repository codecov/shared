# Generated by Django 4.2.11 on 2024-04-25 00:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0015_testresultreporttotals'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportresults',
            name='random_field_reports',
            field=models.IntegerField(null=True),
        ),
    ]
