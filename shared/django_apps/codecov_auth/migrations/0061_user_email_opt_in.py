# Generated by Django 4.2.16 on 2024-10-03 11:55

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    BEGIN;
    --
    -- Add field email_opt_in to user
    --
    ALTER TABLE "users" ADD COLUMN "email_opt_in" boolean DEFAULT false NOT NULL;
    ALTER TABLE "users" ALTER COLUMN "email_opt_in" DROP DEFAULT;
    COMMIT;
    """

    dependencies = [
        ("codecov_auth", "0060_owner_upload_token_required_for_public_repos"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_opt_in",
            field=models.BooleanField(default=False),
        ),
    ]
