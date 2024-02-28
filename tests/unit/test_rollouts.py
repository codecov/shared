from unittest.mock import PropertyMock, patch

from django.test import TestCase

from shared.django_apps.rollouts.models import FeatureFlag, FeatureFlagVariant
from shared.rollouts import Feature


class TestFeature(TestCase):
    def test_buckets(self):
        complex = FeatureFlag.objects.create(
            name="complex", proportion=0.5, salt="random_salt"
        )
        FeatureFlagVariant.objects.create(
            name="complex_a", feature_flag=complex, proportion=1 / 3, value=1
        )
        FeatureFlagVariant.objects.create(
            name="complex_b", feature_flag=complex, proportion=1 / 3, value=2
        )
        FeatureFlagVariant.objects.create(
            name="complex_c", feature_flag=complex, proportion=1 / 3, value=3
        )
        complex_feature = Feature(
            "complex",
            0.5,
        )
        # # To make the math simpler, let's pretend our hash function can only
        # # return 200 different values.
        with patch.object(Feature, "HASHSPACE", 200):

            # Because the top-level feature proportion is 0.5, we are only using the
            # first 50% of our 200 hash values as our test population: [0..100]
            # Each feature variant has a proportion of 1/3, so our three buckets
            # should be [0..33], [34..66], and [67..100]. Anything from [101..200]
            # is not part of the rollout yet.
            buckets = complex_feature._buckets
            assert list(map(lambda x: x[0], buckets)) == [33, 66, 99]

    def test_fully_rolled_out(self):
        rolled_out = FeatureFlag.objects.create(
            name="rolled_out", proportion=1.0, salt="random_salt"
        )
        FeatureFlagVariant.objects.create(
            name="rolled_out_enabled",
            feature_flag=rolled_out,
            proportion=1.0,
            value=True,
        )

        # If the feature is 100% rolled out and only has one variant, then we
        # should skip the hashing and bucket stuff and just return the single
        # possible value.
        feature = Feature("rolled_out", 1.0)
        assert feature.check_value("any", default=False) == True
        assert not hasattr(feature.__dict__, "_buckets")

    def test_overrides(self):
        overrides = FeatureFlag.objects.create(
            name="overrides", proportion=1.0, salt="random_salt"
        )
        FeatureFlagVariant.objects.create(
            name="overrides_a",
            feature_flag=overrides,
            proportion=1 / 2,
            value=1,
            override_owner_ids=[123],
        )
        FeatureFlagVariant.objects.create(
            name="overrides_b",
            feature_flag=overrides,
            proportion=1 / 2,
            value=2,
            override_owner_ids=[321],
        )

        # If an identifier was manually opted into a specific variant, skip the
        # hashing and just return the value for that variant.
        feature = Feature(
            "overrides",
            1.0,
        )

        assert feature.check_value(321, default=1) == 2
        assert feature.check_value(123, default=2) == 1
        assert not hasattr(feature.__dict__, "_buckets")

    def test_not_in_test_gets_default(self):
        not_in_test = FeatureFlag.objects.create(
            name="not_in_test", proportion=0.1, salt="random_salt"
        )
        FeatureFlagVariant.objects.create(
            name="not_in_test_enabled",
            feature_flag=not_in_test,
            proportion=1.0,
            value=True,
        )
        feature = Feature("not_in_test", 0.1)
        # If the feature is only 10% rolled out, 2**128-1 is way past the end of
        # the test population and should get a default value back.
        with patch("mmh3.hash128", return_value=2**128 - 1):
            assert feature.check_value("not in test", default="default") == "default"

    def test_return_values_for_each_bucket(self):
        return_values_for_each_bucket = FeatureFlag.objects.create(
            name="return_values_for_each_bucket", proportion=1.0, salt="random_salt"
        )
        FeatureFlagVariant.objects.create(
            name="return_values_for_each_bucket_a",
            feature_flag=return_values_for_each_bucket,
            proportion=1 / 2,
            value="first bucket",
        )
        FeatureFlagVariant.objects.create(
            name="return_values_for_each_bucket_b",
            feature_flag=return_values_for_each_bucket,
            proportion=1 / 2,
            value="second bucket",
        )

        feature = Feature(
            "return_values_for_each_bucket",
            1.0,
        )
        # To make the math simpler, let's pretend our hash function can only
        # return 100 different values.
        with patch.object(Feature, "HASHSPACE", 100):
            # The feature is 100% rolled out and has two variants at 50% each. So,
            # the buckets are [0..50] and [51..100]. Mock the hash function to
            # return a value in the first bucket and then a value in the second.
            with patch("mmh3.hash128", side_effect=[33, 66]):
                assert feature.check_value("any1", default="c") == "first bucket"
                assert feature.check_value("any2", default="c") == "second bucket"
