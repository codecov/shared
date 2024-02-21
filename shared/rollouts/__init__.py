import mmh3
from cachetools.func import ttl_cache

from shared.django_apps.rollouts.models import FeatureFlag, FeatureFlagVariant


class Feature:
    """
    Represents a feature and its rollout parameters, fetched from the database (see django_apps/rollouts/models.py).
    Given an identifier (repo_id, owner_id, etc..), it can decide which variant of a feature (if any)
    should be enabled for the request. The parameters are fetched and updated roughly every
    5 minutes, meaning it can take up to 5 minutes for changes to show up here. You can modify
    the values via Django Admin.

    If you instantiate a `Feature` instance with a new name, the associated database entry
    will be created for you. Otherwise, the existing database entry will be used to populate
    the values. Also if you change the name of an existing feature, you will need to update
    the name where it is instrumented in the code aswell.

    Examples:

    A simple on/off feature rolled out to 20% of repos:
        # By default, features have no variants — you create them via Django Admin. You also create the `on` variant there.
        MY_FEATURE_BY_REPO = Feature("my_feature", 0.2)

        # DB:
        # FeatureFlagVariant:
        #   name: my_feature_on
        #   feature_flag: my_feature
        #   proportion: 1
        #   enabled: True

    A simple A/B test rolled out to 10% of users (5% test, 5% control):
        MY_EXPERIMENT_BY_USER = Feature(
            "my_experiment",
            0.1,
        )

        # DB:
        # FeatureFlagVariant:
        #   name: MY_EXPERIMENT_BY_USER_TEST
        #   feature_flag: MY_EXPERIMENT_BY_USER
        #   proportion: 0.5
        #   enabled: True
        #
        # FeatureFlagVariant:
        #   name: MY_EXPERIMENT_BY_USER_CONTROL
        #   feature_flag: MY_EXPERIMENT_BY_USER
        #   proportion: 0.5
        #   enabled: False

    After creating a feature, you can instrument it in code like so:
        from shared.rollouts.features import MY_EXPERIMENT_BY_USER
        if MY_EXPERIMENT_BY_USER.is_enabled(user_id, default=False):
            new_behavior()
        else:
            old_behavior()

    Parameters:
    - `name`: a unique name for the experiment.
    - `proportion`: a float between 0 and 1 representing how much of the
      population should get a variant of the feature. 0.5 means 50%.
    - `salt`: a way to effectively re-shuffle which bucket each id falls into

    If you discover a bug and roll back your feature, it's good practice to
    change the salt to any other string before restarting the rollout. Changing
    the salt basically reassigns every id to a new bucket so the same users
    don't feel churned by our rocky rollout.
    """

    HASHSPACE = 2**128

    def __init__(self, name, proportion=None, salt=None):
        assert not proportion or proportion >= 0 and proportion <= 1.0
        assert not salt or isinstance(salt, str)

        ff_query = FeatureFlag.objects.filter(pk=name)

        if len(ff_query) == 0:
            # create default feature flag
            args = {name: name}
            if proportion:
                args["proportion"] = proportion
            if salt:
                args["salt"] = salt

            self.feature_flag = FeatureFlag(**args)
            self.feature_flag.save()
        else:
            # ignore constructor args if db entry already exists.
            self.feature_flag = ff_query.first()

        self.ff_variants = list(
            FeatureFlagVariant.objects.filter(feature_flag=self.feature_flag.name)
        )

    def _fetch_and_set_from_db(self):
        """
        Updates the class with the newest values from database.
        """
        self.feature_flag = FeatureFlag.objects.filter(
            pk=self.feature_flag.name
        ).first()
        self.ff_variants = list(
            FeatureFlagVariant.objects.filter(feature_flag=self.feature_flag.name)
        )

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
        `proportion` and `variants` members. The hash for this repo will fall into
        one of those buckets and the corresponding variant (or default value) will
        be returned.
        """
        test_population = int(self.feature_flag.proportion * Feature.HASHSPACE)

        buckets = []
        quantile = 0
        for variant in self.ff_variants:
            quantile += variant.proportion
            buckets.append((int(quantile * test_population), variant))

        return buckets

    def _get_override_variant(self, identifier):
        """
        Retrieves the FeatureFlagVariant applicable to the given identifer according to
        defined overrides. Returns None if no override is found.
        """
        for variant in self.ff_variants:
            if (
                identifier in variant.override_owner_ids
                or identifier in variant.override_repo_ids
            ):
                return variant
        return None

    def _is_valid_rollout(self):
        """
        Checks if the FeatureFlagVariant entries were given invalid values, which is very
        possible since these values can be modified via Django Admin. Due to the TTL cache,
        the values within this class will only be updated once every 5 minutes.
        """
        return sum(map(lambda x: x.proportion, self.ff_variants)) == 1.0 and not (
            True
            in map(lambda x: x.proportion < 0 or x.proportion > 1, self.ff_variants)
        )

    # NOTE: `@ttl_cache` on instance methods is ordinarily a bad idea:
    # - the cache is not per-instance; it's shared by all class instances
    # - by holding references to function arguments in the cache, it prolongs
    #   their lifetimes. Since `self` is a function argument, the cache will
    #   prevent any instance from getting freed until it is evicted from the
    #   cache which could be a significant memory leak.
    # In this case, we are okay with sharing a cache across instances, and the
    # instances are all global constants so they won't be torn down anyway.
    @ttl_cache(maxsize=64, ttl=300)  # 5 minute ttl
    def is_enabled(self, identifier, default=False):

        # Refresh values from the database. This should only run when the TTL expires,
        # as otherwise, the result of `is_enabled()` should be cached and this function
        # is skipped.
        self._fetch_and_set_from_db()

        if not self._is_valid_rollout():
            # log something
            return False

        identifier = str(identifier)  # just in case

        # check if an override exists
        override_variant = self._get_override_variant(identifier)

        if override_variant:
            return override_variant.enabled

        if self.feature_flag.proportion == 1.0 and len(self.ff_variants) == 1:
            # This feature is fully rolled out, since it only has one variant,
            # we can skip the hashing and just return its value.
            return self.ff_variants.first().enabled

        key = mmh3.hash128(self.feature_flag.name + identifier + self.feature_flag.salt)
        for bucket, variant in self._buckets():
            if key <= bucket:
                return variant.enabled

        return default
