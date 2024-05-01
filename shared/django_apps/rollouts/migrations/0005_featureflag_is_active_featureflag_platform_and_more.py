# Generated by Django 4.2.11 on 2024-05-01 14:14

import django_better_admin_arrayfield.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rollouts", "0004_featureexposure"),
    ]

    # `BEGIN;
    # --
    # -- Add field is_active to featureflag
    # --
    # ALTER TABLE "feature_flags" ADD COLUMN "is_active" boolean DEFAULT true NOT NULL;
    # ALTER TABLE "feature_flags" ALTER COLUMN "is_active" DROP DEFAULT;
    # --
    # -- Add field platform to featureflag
    # --
    # ALTER TABLE "feature_flags" ADD COLUMN "platform" varchar(1) DEFAULT 'B' NOT NULL;
    # ALTER TABLE "feature_flags" ALTER COLUMN "platform" DROP DEFAULT;
    # --
    # -- Add field rollout_identifier to featureflag
    # --
    # ALTER TABLE "feature_flags" ADD COLUMN "rollout_identifier" varchar(30) DEFAULT 'OWNER_ID' NOT NULL;
    # ALTER TABLE "feature_flags" ALTER COLUMN "rollout_identifier" DROP DEFAULT;
    # --
    # -- Add field override_emails to featureflagvariant
    # --
    # ALTER TABLE "feature_flag_variants" ADD COLUMN "override_emails" varchar[] DEFAULT '{}' NOT NULL;
    # ALTER TABLE "feature_flag_variants" ALTER COLUMN "override_emails" DROP DEFAULT;
    # --
    # -- Add field override_org_ids to featureflagvariant
    # --
    # ALTER TABLE "feature_flag_variants" ADD COLUMN "override_org_ids" integer[] DEFAULT '{}' NOT NULL;
    # ALTER TABLE "feature_flag_variants" ALTER COLUMN "override_org_ids" DROP DEFAULT;
    # COMMIT;

    operations = [
        migrations.AddField(
            model_name="featureflag",
            name="is_active",
            field=models.BooleanField(
                default=True,
                help_text="This should be on if the experiment is currently running. Otherwise turn it off if the experiment has finished and is cleaned up",
            ),
        ),
        migrations.AddField(
            model_name="featureflag",
            name="platform",
            field=models.CharField(
                choices=[("F", "Frontend"), ("B", "Backend")], default="B", max_length=1
            ),
        ),
        migrations.AddField(
            model_name="featureflag",
            name="rollout_identifier",
            field=models.CharField(
                choices=[
                    ("OWNER_ID", "Owner ID"),
                    ("REPO_ID", "Repo ID"),
                    ("ORG_ID", "Org ID"),
                    ("EMAIL", "Email"),
                ],
                default="OWNER_ID",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="featureflagvariant",
            name="override_emails",
            field=django_better_admin_arrayfield.models.fields.ArrayField(
                base_field=models.CharField(), blank=True, default=list, size=None
            ),
        ),
        migrations.AddField(
            model_name="featureflagvariant",
            name="override_org_ids",
            field=django_better_admin_arrayfield.models.fields.ArrayField(
                base_field=models.IntegerField(), blank=True, default=list, size=None
            ),
        ),
    ]
