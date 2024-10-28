import json
import logging
import os
from functools import cached_property
from typing import Optional

import mmh3
from asgiref.sync import sync_to_async
from cachetools.func import lru_cache, ttl_cache
from django.utils import timezone

from shared.config import get_config
from shared.django_apps.rollouts.models import (
    FeatureExposure,
    FeatureFlag,
    FeatureFlagVariant,
    Platform,
    RolloutUniverse,
)
from shared.django_apps.utils.model_utils import rollout_universe_to_override_string

log = logging.getLogger("__name__")


class Feature:
    """
    Represents a feature and its rollout parameters, fetched from the database (see django_apps/rollouts/models.py).
    Given an identifier (repo_id, owner_id, etc..), it will decide which variant of a feature should be
    used for the request. Each variant will have a `value` that will be returned if that variant is decided to
    be used. For example: if you want an ON and OFF variant for your feature, you could have the values
    be true and false respectively

    You can modify the parameters of your feature flag via Django Admin. The parameters are fetched and updated roughly
    every 5 minutes, meaning it can take up to 5 minutes for changes to show up here.

    If you manage your own deployment, you can disable or override feature checks with environment variables:
    - If `CODECOV__FEATURE__{name.upper()}` is set, its value will be deserialized as JSON and returned for the
      `Feature` with that name
    - If `CODECOV__FEATURE__DISABLE` is set, checks will be skipped and default values will be returned every time
      for every feature except those with overrides set via `CODECOV__FEATURE__{name.upper()}` env vars

    If you instantiate a `Feature` instance with a new name, the associated database entry
    will be created for you. Otherwise, the existing database entry will be used to populate
    the values. Also if you change the name of an existing feature, you will need to update
    the name where it is instrumented in the code aswell.

    Examples:

    A simple on/off feature rolled out to 20% of repos:
        # By default, features have no variants — you create them via Django Admin. You can create the `on`
        # variant there, along with setting the proportion and salt for the flag.
        MY_FEATURE_BY_REPO = Feature("my_feature")

        # DB:
        # FeatureFlag:
        #   name: my_feature
        #   proportion: 0.0 # default value
        #   salt: ajsdopijaejapvjghiujnarapsjf # default is randomly generated
        #
        # FeatureFlagVariant:
        #   name: my_feature_on
        #   feature_flag: my_feature
        #   proportion: 1
        #   value: true

    A simple A/B test rolled out to 10% of users (5% test, 5% control):
        MY_EXPERIMENT_BY_USER = Feature("my_experiment")

        # DB:
        # FeatureFlag:
        #   name: my_experiment
        #   proportion: 0.1
        #   salt: foajdisjfosdjrandomfsfsdfsfsfs
        #
        # FeatureFlagVariant:
        #   name: test
        #   feature_flag: my_experiment
        #   proportion: 0.5
        #   value: true
        #
        # FeatureFlagVariant:
        #   name: control
        #   feature_flag: my_experiment
        #   proportion: 0.5
        #   value: false

    After creating a feature, you can instrument it in code like so:
        from shared.rollouts.features import MY_EXPERIMENT_BY_USER
        if MY_EXPERIMENT_BY_USER.check_value(user_id, default=False) == True:
            new_behavior()
        else:
            old_behavior()

    Parameters:
    - `name`: the unique name of your feature flag you created in django admin

    If you discover a bug and roll back your feature, it's good practice to
    change the salt to any other string before restarting the rollout. Changing
    the salt basically reassigns every id to a new bucket so the same users
    don't feel churned by our rocky rollout.
    """

    HASHSPACE = 2**128

    def __init__(
        self,
        name,
        feature_flag: Optional[FeatureFlag] = None,
        ff_variants: Optional[list[FeatureFlagVariant]] = None,
    ):
        self.name = name
        self.feature_flag = feature_flag
        self.ff_variants = ff_variants

        # See if this environment has disabled feature flagging entirely.
        # These environments will always get default values.
        self.env_disable = os.getenv("CODECOV__FEATURE__DISABLE") is not None

        # See if this environment has provided an override for this feature in
        # its environment variables. Since feature variant values are stored in
        # the database as JSON, we read these overrides as JSON as well.
        #
        # We need to be able to tell the difference between the case where an
        # override is _undefined_ and the case where the override is defined and
        # set to `"null"`/`None`. Two cases:
        # - If the override is defined, `hasattr(self, 'env_override') == True`
        # - If the override is undefined, `hasattr(self, 'env_override') == False`
        env_override = os.getenv(f"CODECOV__FEATURE__{name.upper()}")
        if env_override is not None:
            self.env_override = json.loads(env_override or '""')

        self.refresh = get_config(
            "setup", "skip_feature_cache", default=False
        )  # to be used only during development
        if self.refresh:
            log.warning(
                "skip_feature_cache for Feature should only be turned on in development environments, and should not be used in production"
            )

    def check_value(self, identifier, default=False):
        """
        Returns the value of the applicable feature variant for an identifier. This is commonly a boolean for feature variants
        that represent an ON variant and an OFF variant, but could be other values aswell. You can modify the values in
        feature variants via Django Admin.
        """

        if hasattr(self, "env_override"):
            return self.env_override

        if self.env_disable:
            return default

        if self.refresh:
            self._fetch_and_set_from_db.cache_clear()

        # Will only run and refresh values from the database every ~5 minutes due to TTL cache
        self._fetch_and_set_from_db()

        return self._check_value(identifier, default)

    @sync_to_async
    def check_value_async(self, identifier, default=False):
        return self.check_value(identifier, default)

    def check_value_no_fetch(self, identifier, default=False):
        """
        Same as `check_value()` except does not make any DB calls, and assumes the flag data has been passed into the class
        during object initialization.
        """
        if hasattr(self, "env_override"):
            return self.env_override

        if self.env_disable:
            return default

        return self._check_value_no_lru(identifier, False)

    @cached_property
    def _buckets(self):
        """
        Calculates the bucket boundaries for feature variants. Simple logic but
        the use of floats and int casting may introduce error.

        To check if a feature should be enabled for a specific repo (for instance)
        this class will compute a hash including:
        - The experiment's name
        - The repo's id
        - A salt

        The range of possible hash values is divvied up into buckets based on the
        `proportion` of the feature flag and its `variants`. The hash for this repo
        will fall into one of those buckets and the corresponding variant (or default
        value) will be returned.

        Each bucket in the buckets array represents a range: (0, 1000, `enabled_variant`). In
        this case, hashes that land in [0, 1000) will be assigned `enabled_variant`
        """

        buckets = []
        quantile = 0

        for variant in self.ff_variants:
            variant_test_population = int(variant.proportion * Feature.HASHSPACE)

            start = int(quantile * Feature.HASHSPACE)
            end = int(start + (variant_test_population * self.feature_flag.proportion))

            quantile += variant.proportion
            buckets.append((start, end, variant))

        return buckets

    def _get_override_variant(self, identifier, identifier_override_field):
        """
        Retrieves the feature variant applicable to the given identifer according to
        the defined applicable overrides. Returns None if no override is found.
        """
        for variant in self.ff_variants:
            if identifier in getattr(variant, identifier_override_field):
                return variant
        return None

    def _is_valid_rollout(self):
        """
        Checks if the database entries were given valid values, which is very
        possible since these values can be modified via Django Admin. Sum of
        variants should equal to 1, and proportions should never be greater than
        1 or less than 0.
        """
        variant_proportion_sum = sum(map(lambda x: x.proportion, self.ff_variants))
        variant_proportions_in_range = True not in map(
            lambda x: x.proportion < 0 or x.proportion > 1, self.ff_variants
        )
        feature_proportion_in_range = (
            self.feature_flag.proportion <= 1 and self.feature_flag.proportion >= 0
        )
        return (
            (variant_proportion_sum == 1.0 or variant_proportion_sum == 0.0)
            and variant_proportions_in_range
            and feature_proportion_in_range
        )

    @ttl_cache(maxsize=64, ttl=300)  # 5 minute time-to-live cache
    def _fetch_and_set_from_db(self):
        """
        Updates the instance with the newest values from database, and clears other caches so
        that their values can be recalculated.
        """
        new_feature_flag = FeatureFlag.objects.filter(pk=self.name).first()
        new_ff_variants = sorted(
            list(FeatureFlagVariant.objects.filter(feature_flag=self.name)),
            key=lambda x: x.variant_id,
        )

        if not new_feature_flag:
            # create default feature flag
            new_feature_flag = FeatureFlag.objects.create(name=self.name)

        clear_cache = False

        # Either completely new or different from what we got last time
        if (not self.feature_flag) or self._is_different(
            new_feature_flag, self.feature_flag
        ):
            self.feature_flag = new_feature_flag
            clear_cache = True
        if (not self.ff_variants) or len(self.ff_variants) != len(new_ff_variants):
            self.ff_variants = new_ff_variants
            clear_cache = True
        else:
            for ind in range(len(new_ff_variants)):
                if self._is_different(new_ff_variants[ind], self.ff_variants[ind]):
                    self.ff_variants = new_ff_variants
                    clear_cache = True
                    break

        if clear_cache:
            self._check_value.cache_clear()

            if hasattr(self, "_buckets"):
                del self._buckets  # clears @cached_property

        if not self._is_valid_rollout():
            log.warning(
                "Feature flag is using invalid values for rollout",
                extra=dict(feature_flag_name=self.name),
            )

    # NOTE: `@lru_cache` on instance methods is ordinarily a bad idea:
    # - the cache is not per-instance; it's shared by all class instances
    # - by holding references to function arguments in the cache, it prolongs
    #   their lifetimes. Since `self` is a function argument, the cache will
    #   prevent any instance from getting freed until it is evicted from the
    #   cache which could be a significant memory leak.
    # In this case, we are okay with sharing a cache across instances, and the
    # instances are all global constants so they won't be torn down anyway.
    @lru_cache(maxsize=64)
    def _check_value(self, identifier, default):
        """
        This function will have its cache invalidated when `_fetch_and_set_from_db()` pulls new data so that
        variant values can be returned using the most up-to-date values from the database.
        """
        return self._check_value_impl(identifier, default)

    def _check_value_no_lru(self, identifier, default):
        """
        Same as `_check_value()` except no lru cache. This is used by the `/internal/features` endpoint and can't
        use lru as it would prevent class instances from getting garbage collected, as the endpoint instantiates
        the `Feature` class on every request.
        """

        # don't log exposures for flag evaluations from the endpoint
        return self._check_value_impl(identifier, default, log_exposures=False)

    def _check_value_impl(self, identifier, default, log_exposures=True):
        """
        This is the core logic of how a feature flag variant is assigned to a user based on some identifier, and
        returns the variant's value.
        """
        # check if an override exists
        identifier_override_field = rollout_universe_to_override_string(
            self.feature_flag.rollout_universe
        )
        override_variant = self._get_override_variant(
            identifier, identifier_override_field
        )

        if override_variant:
            return override_variant.value

        if self.feature_flag.proportion == 1.0 and len(self.ff_variants) == 1:
            # This feature is fully rolled out, since it only has one variant,
            # we can skip the hashing and just return its value.
            return self.ff_variants[0].value

        key = mmh3.hash128(
            self.feature_flag.name + str(identifier) + self.feature_flag.salt
        )
        for bucket_start, bucket_end, variant in self._buckets:
            if bucket_start <= key and key < bucket_end:
                # only log exposures for backend flags because frontend has no SQL metrics and
                # flag evaluations should be cached client-side anyways
                if self.feature_flag.platform == Platform.BACKEND and log_exposures:
                    self.create_exposure(variant, identifier)

                return variant.value

        return default

    def _is_different(self, inst1, inst2):
        fields = inst1._meta.get_fields()

        for field in fields:
            if isinstance(field, str) and getattr(inst1, field) != getattr(
                inst2, field
            ):
                return False

        return True

    def create_exposure(self, variant, identifier):
        """
        Creates an exposure record indicating that a feature variant has been applied to
        an entity (repo or owner) at a current point in time. This method should only
        be used for backend feature flags, as we're only collecting `telemetry_simple`
        SQL metrics for backend services.
        """
        args = {
            "feature_flag": self.feature_flag,
            "feature_flag_variant": variant,
            "timestamp": timezone.now(),
        }
        if self.feature_flag.rollout_universe == RolloutUniverse.OWNER_ID:
            args["owner"] = identifier
        elif self.feature_flag.rollout_universe == RolloutUniverse.REPO_ID:
            args["repo"] = identifier

        FeatureExposure.objects.create(**args)
