# Generated by Django 4.2.11 on 2024-05-07 18:40

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    BEGIN;
    --
    -- Remove index i_owner from usermeasurement
    --
    DROP INDEX IF EXISTS "i_owner";
    --
    -- Remove index owner_repo from usermeasurement
    --
    DROP INDEX IF EXISTS "owner_repo";
    --
    -- Remove index owner_private_repo from usermeasurement
    --
    DROP INDEX IF EXISTS "owner_private_repo";
    --
    -- Remove index owner_private_repo_report_type from usermeasurement
    --
    DROP INDEX IF EXISTS "owner_private_repo_report_type";
    --
    -- Remove field commit from usermeasurement
    --
    ALTER TABLE "user_measurements" DROP COLUMN "commit_id" CASCADE;
    --
    -- Remove field owner from usermeasurement
    --
    ALTER TABLE "user_measurements" DROP COLUMN "owner_id" CASCADE;
    --
    -- Remove field repo from usermeasurement
    --
    ALTER TABLE "user_measurements" DROP COLUMN "repo_id" CASCADE;
    --
    -- Remove field upload from usermeasurement
    --
    ALTER TABLE "user_measurements" DROP COLUMN "upload_id" CASCADE;
    --
    -- Add field commit_id to usermeasurement
    --
    ALTER TABLE "user_measurements" ADD COLUMN "commit_id" integer NULL;
    --
    -- Add field owner_id to usermeasurement
    --
    ALTER TABLE "user_measurements" ADD COLUMN "owner_id" integer NULL;
    --
    -- Add field repo_id to usermeasurement
    --
    ALTER TABLE "user_measurements" ADD COLUMN "repo_id" integer NULL;
    --
    -- Add field upload_id to usermeasurement
    --
    ALTER TABLE "user_measurements" ADD COLUMN "upload_id" integer NULL;
    --
    -- Create index i_owner on field(s) owner_id of model usermeasurement
    --
    CREATE INDEX "i_owner" ON "user_measurements" ("owner_id");
    --
    -- Create index owner_repo on field(s) owner_id, repo_id of model usermeasurement
    --
    CREATE INDEX "owner_repo" ON "user_measurements" ("owner_id", "repo_id");
    --
    -- Create index owner_private_repo on field(s) owner_id, private_repo of model usermeasurement
    --
    CREATE INDEX "owner_private_repo" ON "user_measurements" ("owner_id", "private_repo");
    --
    -- Create index owner_private_repo_report_type on field(s) owner_id, private_repo, report_type of model usermeasurement
    --
    CREATE INDEX "owner_private_repo_report_type" ON "user_measurements" ("owner_id", "private_repo", "report_type");
    COMMIT;
    """

    dependencies = [
        ("user_measurements", "0001_initial"),
    ]

    operations = [
        migrations.RiskyRemoveIndex(
            model_name="usermeasurement",
            name="i_owner",
        ),
        migrations.RiskyRemoveIndex(
            model_name="usermeasurement",
            name="owner_repo",
        ),
        migrations.RiskyRemoveIndex(
            model_name="usermeasurement",
            name="owner_private_repo",
        ),
        migrations.RiskyRemoveIndex(
            model_name="usermeasurement",
            name="owner_private_repo_report_type",
        ),
        migrations.RiskyRemoveField(
            model_name="usermeasurement",
            name="commit",
        ),
        migrations.RiskyRemoveField(
            model_name="usermeasurement",
            name="owner",
        ),
        migrations.RiskyRemoveField(
            model_name="usermeasurement",
            name="repo",
        ),
        migrations.RiskyRemoveField(
            model_name="usermeasurement",
            name="upload",
        ),
        migrations.RiskyAddField(
            model_name="usermeasurement",
            name="commit_id",
            field=models.IntegerField(null=True),
        ),
        migrations.RiskyAddField(
            model_name="usermeasurement",
            name="owner_id",
            field=models.IntegerField(null=True),
        ),
        migrations.RiskyAddField(
            model_name="usermeasurement",
            name="repo_id",
            field=models.IntegerField(null=True),
        ),
        migrations.RiskyAddField(
            model_name="usermeasurement",
            name="upload_id",
            field=models.IntegerField(null=True),
        ),
        migrations.RiskyAddIndex(
            model_name="usermeasurement",
            index=models.Index(fields=["owner_id"], name="i_owner"),
        ),
        migrations.RiskyAddIndex(
            model_name="usermeasurement",
            index=models.Index(fields=["owner_id", "repo_id"], name="owner_repo"),
        ),
        migrations.RiskyAddIndex(
            model_name="usermeasurement",
            index=models.Index(
                fields=["owner_id", "private_repo"], name="owner_private_repo"
            ),
        ),
        migrations.RiskyAddIndex(
            model_name="usermeasurement",
            index=models.Index(
                fields=["owner_id", "private_repo", "report_type"],
                name="owner_private_repo_report_type",
            ),
        ),
    ]
