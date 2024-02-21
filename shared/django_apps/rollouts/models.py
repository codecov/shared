from random import choice

from django.contrib.postgres import fields
from django.db import models


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
    proportion = models.DecimalField(default=0, decimal_places=3, max_digits=4)
    salt = models.CharField(max_length=10000, default=default_random_salt)

    class Meta:
        db_table = "feature_flags"
        constraints = [
            models.UniqueConstraint(fields=["name"], name="feature_flag_name")
        ]
        # TODO: assert that variant proportions sum to 1


class FeatureFlagVariant(models.Model):
    """
    Represents a variant of the feature being rolled out and the proportion of
    the test population it should be rolled out to (see shared/rollouts/__init__.py).
    The proportion should be a float between 0 and 1. A proportion of 0.5 means 50% of
    the test population should receive this variant. Ensure that for any `FeatureFlag`,
    the proportions of the corresponding `FeatureFlagVariant`s sum to 1.
    """

    name = models.CharField(max_length=200, primary_key=True)  
    feature_flag = models.ForeignKey(
        "FeatureFlag", on_delete=models.CASCADE, related_name="variants"
    )
    proportion = models.DecimalField(default=0, decimal_places=3, max_digits=4)
    enabled = models.BooleanField(default=False)

    # Weak foreign keys to Owner and Respository models respectively
    override_owner_ids = fields.ArrayField(
        base_field=models.IntegerField(), default=list
    )
    override_repo_ids = fields.ArrayField(
        base_field=models.IntegerField(), default=list
    )

    # TODO: maybe add more fields for more granularity on feature variants. EG: featureA uses value 10 vs featureB uses value 100
    class Meta:
        db_table = "feature_flag_variants"
        constraints = [
            models.UniqueConstraint(fields=["name"], name="feature_flag_variant_name")
        ]
        indexes = [models.Index(fields=["feature_flag"])]
