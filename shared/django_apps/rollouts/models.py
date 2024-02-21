from random import choice

from django.contrib.postgres import fields
from django.db import models


def default_random_salt():
    chars = []
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for _ in range(16):
        chars.append(choice(ALPHABET))
    return "".join(chars)


class FeatureFlag(models.Model):
    name = models.CharField(max_length=200, primary_key=True)
    proportion = models.DecimalField(default=0, decimal_places=3, max_digits=3)
    salt = models.CharField(max_length=10000, default=default_random_salt)

    class Meta:
        db_table = "feature_flags"
        constraints = [
            models.UniqueConstraint(fields=["name"], name="feature_flag_name")
        ]
        # TODO: assert that variant proportions sum to 1


class FeatureFlagVariant(models.Model):
    name = models.CharField(max_length=200, primary_key=True)
    feature_flag = models.ForeignKey(
        "FeatureFlag", on_delete=models.CASCADE, related_name="variants"
    )
    proportion = models.DecimalField(default=0, decimal_places=3, max_digits=3)
    enabled = models.BooleanField(default=False)
    override_owner_ids = fields.ArrayField(base_field=models.IntegerField(), default=list)
    override_repo_ids = fields.ArrayField(base_field=models.IntegerField(), default=list)
    # TODO: maybe add more fields for more granularity on feature variants. EG: featureA uses value 10 vs featureB uses value 100

    class Meta:
        db_table = "feature_flag_variants"
        constraints = [
            models.UniqueConstraint(fields=["name"], name="feature_flag_variant_name")
        ]
        indexes = [models.Index(fields=["feature_flag"])]

