# Generated by Django 4.2.7 on 2024-02-19 23:18

import django.contrib.postgres.fields
import django.db.models.deletion
from django.db import migrations, models

import shared.django_apps.rollouts.models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FeatureFlag",
            fields=[
                (
                    "name",
                    models.CharField(max_length=200, primary_key=True, serialize=False),
                ),
                (
                    "proportion",
                    models.DecimalField(decimal_places=3, default=0, max_digits=3),
                ),
                (
                    "salt",
                    models.CharField(
                        default=shared.django_apps.rollouts.models.default_random_salt,
                        max_length=10000,
                    ),
                ),
            ],
            options={
                "db_table": "feature_flags",
            },
        ),
        migrations.CreateModel(
            name="FeatureFlagVariant",
            fields=[
                (
                    "name",
                    models.CharField(max_length=200, primary_key=True, serialize=False),
                ),
                (
                    "proportion",
                    models.DecimalField(decimal_places=3, default=0, max_digits=3),
                ),
                ("enabled", models.BooleanField(default=False)),
                (
                    "feature_flag",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="variants",
                        to="rollouts.featureflag",
                    ),
                ),
            ],
            options={
                "db_table": "feature_flag_variants",
            },
        ),
        migrations.CreateModel(
            name="FeatureFlagRepoOverride",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "repo_ids",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.IntegerField(), size=None
                    ),
                ),
                (
                    "feature",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="repo_overrides",
                        to="rollouts.featureflag",
                    ),
                ),
                (
                    "variant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="repo_overrides",
                        to="rollouts.featureflagvariant",
                    ),
                ),
            ],
            options={
                "db_table": "feature_flag_repo_overrides",
            },
        ),
        migrations.CreateModel(
            name="FeatureFlagOwnerOverride",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "owner_ids",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.IntegerField(), size=None
                    ),
                ),
                (
                    "feature",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="owner_overrides",
                        to="rollouts.featureflag",
                    ),
                ),
                (
                    "variants",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="owner_overrides",
                        to="rollouts.featureflagvariant",
                    ),
                ),
            ],
            options={
                "db_table": "feature_flag_owner_overrides",
            },
        ),
        migrations.AddConstraint(
            model_name="featureflag",
            constraint=models.UniqueConstraint(
                fields=("name",), name="feature_flag_name"
            ),
        ),
        migrations.AddConstraint(
            model_name="featureflagvariant",
            constraint=models.UniqueConstraint(
                fields=("name",), name="feature_flag_variant_name"
            ),
        ),
    ]
