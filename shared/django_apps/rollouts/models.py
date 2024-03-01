from random import choice

from django.core.exceptions import ValidationError
from django.db import models
from django_better_admin_arrayfield.models.fields import ArrayField


# TODO: move to utils
def default_random_salt():
    chars = []
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for _ in range(16):
        chars.append(choice(ALPHABET))
    return "".join(chars)


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

    # Weak foreign keys to Owner and Respository models respectively
    override_owner_ids = ArrayField(
        base_field=models.IntegerField(), default=list, blank=True
    )
    override_repo_ids = ArrayField(
        base_field=models.IntegerField(), default=list, blank=True
    )

    class Meta:
        db_table = "feature_flag_variants"
        indexes = [models.Index(fields=["feature_flag"])]

    def __str__(self):
        return self.feature_flag.__str__() + ": " + self.name


class FeatureExposure(models.Model):
    """
    Represents a feature variant being exposed to an entity (repo or owner) at
    a point in time. Used to keep track of when features and variants have been enabled
    and who they affected for metrics purposes.
    """

    exposure_id = models.AutoField(primary_key=True)
    feature_flag = models.ForeignKey(
        "FeatureFlag", on_delete=models.CASCADE, related_name="exposures"
    )
    feature_flag_variant = models.ForeignKey(
        "FeatureFlagVariant", on_delete=models.CASCADE, related_name="exposures"
    )

    # Weak foreign keys to Owner and Respository models respectively
    owner = models.IntegerField(null=True, blank=True)
    repo = models.IntegerField(null=True, blank=True)

    timestamp = models.DateTimeField(null=False)

    def clean(self):
        if not self.owner and not self.repo:
            raise ValidationError(
                "Exposure must have either a corresponding owner or repo"
            )

        super(FeatureExposure, self).clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super(FeatureExposure, self).save(*args, **kwargs)

    class Meta:
        db_table = "feature_exposures"
        # indexes = [ # don't use indexes for now
        #     models.Index(fields=['feature_flag', 'timestamp'], name='feature_flag_timestamp_idx'),
        # ]
