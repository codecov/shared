from functools import cached_property, lru_cache

import mmh3


class FeatureVariant:
    """
    Represents a variant of the feature being rolled out and the proportion of
    the test population it should be rolled out to. The proportion should be a
    float between 0 and 1. A proportion of 0.5 means 50% of the test population
    should receive this variant.

    A simple on/off feature rollout will have one variant:
        {"enabled": FeatureVariant(True, 1.0)}

    A simple A/B test will have two variants:
        {
            "test": FeatureVariant(True, 0.5),
            "control": FeatureVariant(False, 0.5),
        }
    """

    def __init__(self, value, proportion):
        assert proportion > 0 and proportion <= 1.0
        self.value = value
        self.proportion = proportion


class Feature:
    """
    Represents a feature and its rollout parameters. Given an identifier, it can
    decide which variant of a feature (if any) should be enabled for the
    request.

    A simple on/off feature rolled out to 20% of repos:
        # By default, features have a single variant:
        #   {"enabled": FeatureVariant(True, 1.0)}
        MY_FEATURE_BY_REPO = Feature("my_feature", 0.2)

    A simple A/B test rolled out to 10% of users (5% test, 5% control):
        MY_EXPERIMENT_BY_USER = Feature(
            "my_experiment",
            0.1,
            variants={
                "test": FeatureVariant(True, 0.5),
                "control": FeatureVariant(False, 0.5),
            },
        )

    After creating a feature, you can check it in code like so:
        from shared.rollouts.features import MY_FEATURE
        if MY_FEATURE.check_value(user_id, default=False):
            new_behavior()

    You can roll a feature out to different populations by passing in different
    identifiers:
    - pass in a user id to roll out to X% of users
    - pass in a repo id to roll out to X% of repos
    - pass in an org id to roll out to X% of orgs
    - pass in a sentry trace id or similar to roll out to X% of requests

    Try to be consistent - if you pass a repo id in one place, pass a repo id
    everywhere (including in overrides).

    Parameters:
    - `name`: a unique name for the experiment.
    - `proportion`: a float between 0 and 1 representing how much of the
      population should get a variant of the feature. 0.5 means 50%.
    - `variants`: a dictionary {name: FeatureVariant()}. The default value works
      for a simple on/off feature rollout.
    - `salt`: a way to effectively re-shuffle which bucket each id falls into
    - `overrides`: a dictionary {id: variant name}. Used to opt specific repos
      into a specific feature variant for example.

    If you discover a bug and roll back your feature, it's good practice to
    change the salt to any other string before restarting the rollout. Changing
    the salt basically reassigns every id to a new bucket so the same users
    don't feel churned by our rocky rollout.
    """

    HASHSPACE = 2**128

    def __init__(
        self,
        name,
        proportion,
        variants={"enabled": FeatureVariant(True, 1.0)},
        salt="",
        overrides={},
    ):
        assert sum(map(lambda x: x.proportion, variants.values())) == 1.0
        assert proportion > 0 and proportion <= 1.0
        self.name = name
        self.proportion = proportion
        self.variants = variants
        self.salt = salt
        self.overrides = overrides

    @cached_property
    def _buckets(self):
        """
        Calculates the bucket boundaries for feature variants. Simple logic but
        the use of floats and int casting may introduce error.

        To check if a feature should be enabled for a specific repo (for instance)
        this class will compute a hash including:
        - The experiment's name
        - The repo's id
        - (Optional) A unique salt

        The range of possible hash values is divvied up into buckets based on the
        `proportion` and `variants` members. The hash for this repo will fall into
        one of those buckets and the corresponding variant (or default value) will
        be returned.
        """
        test_population = int(self.proportion * Feature.HASHSPACE)

        buckets = []
        quantile = 0
        for variant in self.variants.values():
            quantile += variant.proportion
            buckets.append((int(quantile * test_population), variant))

        return buckets

    # NOTE: `@lru_cache` on instance methods is ordinarily a bad idea:
    # - the cache is not per-instance; it's shared by all class instances
    # - by holding references to function arguments in the cache, it prolongs
    #   their lifetimes. Since `self` is a function argument, the cache will
    #   prevent any instance from getting freed until it is evicted from the
    #   cache which could be a significant memory leak.
    # In this case, we are okay with sharing a cache across instances, and the
    # instances are all global constants so they won't be torn down anyway.
    @lru_cache(maxsize=50)
    def check_value(self, identifier, default=None):
        identifer = str(identifier)  # just in case
        if identifier in self.overrides:
            override_variant = self.overrides[identifier]
            return self.variants[override_variant].value
        elif self.proportion == 1.0 and len(self.variants) == 1:
            # This feature is fully rolled out, since it only has one variant,
            # we can skip the hashing and just return its value.
            return next(iter(self.variants.values())).value

        key = mmh3.hash128(self.name + identifier + self.salt)
        for bucket, variant in self._buckets:
            if key <= bucket:
                return variant.value

        return default
