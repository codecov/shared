from django.db import models
from django_better_admin_arrayfield.models.fields import ArrayField


# Defines whether flag is a front/back end feature flag. Backend
# flags benefit from experimentation via `telemetry_simple` SQL metrics
class Platform(models.TextChoices):
    FRONTEND = "F", "Frontend"
    BACKEND = "B", "Backend"


# Defines the possible identifiers you can perform a rollout over. Users
# who share the same identifier will always be assigned the same variant.
# EG: two users from the same org will receive the same variant when rolling
# out over ORG_ID
class RolloutUniverse(models.TextChoices):
    OWNER_ID = "OWNER_ID", "Owner ID"
    REPO_ID = "REPO_ID", "Repo ID"
    ORG_ID = "ORG_ID", "Org ID"
    EMAIL = "EMAIL", "Email"


def default_random_salt():
    # to resolve circular dependency
    from shared.django_apps.utils.rollout_utils import default_random_salt

    return default_random_salt()


class FeatureFlag(models.Model):
    """
    Represents a feature and its rollout parameters (see shared/rollouts/__init__.py). A
    default salt will be created if one is not provided.
    """

    name = models.CharField(max_length=200, primary_key=True)
    proportion = models.DecimalField(
        default=0,
        decimal_places=3,
        max_digits=4,
        help_text="Values are between 0 and 1. Eg: 0.5 means 50% of users",
    )
    salt = models.CharField(max_length=32, default=default_random_salt)
    platform = models.CharField(
        max_length=1, choices=Platform.choices, default=Platform.BACKEND
    )
    # Represents if an experiment has been cleaned up and
    # is no longer running anymore
    is_active = models.BooleanField(
        default=True,
        help_text="This should be on if the experiment is currently running. Otherwise turn it off if the experiment has finished and is cleaned up",
    )

    # The field we're rolling out over. Users with the same identifier
    # will always receive the same variant. EG: if you rollout over org_id,
    # then users in the same org see the same variant
    rollout_universe = models.CharField(
        max_length=30,
        choices=RolloutUniverse.choices,
        default=RolloutUniverse.OWNER_ID,
    )

    class Meta:
        db_table = "feature_flags"

    def __str__(self):
        return self.name


class FeatureFlagVariant(models.Model):
    """
    Represents a variant of the feature being rolled out and the proportion of
    the test population it should be rolled out to (see shared/rollouts/__init__.py).
    The proportion should be a float between 0 and 1. A proportion of 0.5 means 50% of
    the test population should receive this variant. Ensure that for any `FeatureFlag`,
    the proportions of the corresponding `FeatureFlagVariant`s sum to 1.
    """

    variant_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    feature_flag = models.ForeignKey(
        "FeatureFlag", on_delete=models.CASCADE, related_name="variants"
    )
    proportion = models.DecimalField(
        default=0,
        decimal_places=3,
        max_digits=4,
        help_text="Values are between 0 and 1. Eg: 0.5 means 50% of users. The sum of all variants' proportions for a feature should equal to 1.",
    )
    value = models.JSONField(
        default=False,
        help_text="Accepts JSON values. Eg: `true`, `false`, `10`, `['abc', 'def']`, `{'k': 'v'}`",
    )

    # Weak foreign keys to Owner and Respository models respectively. These
    # same fields are also referenced for `telemetry_simple` metrics, and are
    # connected via FeatureExposure to allow for experimentation.
    override_owner_ids = ArrayField(
        base_field=models.IntegerField(), default=list, blank=True
    )
    override_repo_ids = ArrayField(
        base_field=models.IntegerField(), default=list, blank=True
    )

    # Email field of Owner model
    override_emails = ArrayField(
        base_field=models.CharField(), default=list, blank=True
    )
    # Foreign key to Owner model (orgs and users are both Owner model)
    override_org_ids = ArrayField(
        base_field=models.IntegerField(), default=list, blank=True
    )

    class Meta:
        db_table = "feature_flag_variants"
        indexes = [models.Index(fields=["feature_flag"])]

    def __str__(self):
        return self.feature_flag.__str__() + ": " + self.name
