# Generated by Django 4.2.11 on 2024-07-10 14:28

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    BEGIN;
    --
    -- Create model CacheConfig
    --
    CREATE TABLE "bundle_analysis_app_cacheconfig" (
        "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
        "repo_id" integer NOT NULL,
        "bundle_name" varchar NOT NULL,
        "is_caching" boolean NOT NULL,
        "created_at" timestamp with time zone NOT NULL,
        "updated_at" timestamp with time zone NOT NULL
    );
    --
    -- Create constraint unique_repo_bundle_pair on model cacheconfig
    --
    ALTER TABLE "bundle_analysis_app_cacheconfig" ADD CONSTRAINT "unique_repo_bundle_pair" UNIQUE (
        "repo_id", "bundle_name"
    );
    COMMIT;
    """

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CacheConfig",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("repo_id", models.IntegerField()),
                ("bundle_name", models.CharField()),
                ("is_caching", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="cacheconfig",
            constraint=models.UniqueConstraint(
                fields=("repo_id", "bundle_name"), name="unique_repo_bundle_pair"
            ),
        ),
    ]