from unittest.mock import patch

from django.core.exceptions import SynchronousOnlyOperation
from django.test import TestCase

from shared.django_apps.rollouts.models import (
    FeatureExposure,
    FeatureFlag,
    FeatureFlagVariant,
)
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
        complex_feature = Feature("complex")

        # # To make the math simpler, let's pretend our hash function can only
        # # return 200 different values.
        with patch.object(Feature, "HASHSPACE", 200):

            complex_feature.check_value(owner_id=1234)  # to force fetch values from db

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
        feature = Feature("rolled_out")
        assert feature.check_value(owner_id=123, default=False) == True
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
        )

        assert feature.check_value(owner_id=321, default=1) == 2
        assert feature.check_value(owner_id=123, default=2) == 1
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
        feature = Feature("not_in_test")
        # If the feature is only 10% rolled out, 2**128-1 is way past the end of
        # the test population and should get a default value back.
        with patch("mmh3.hash128", return_value=2**128 - 1):
            assert feature.check_value(owner_id=123, default="default") == "default"

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

        feature = Feature("return_values_for_each_bucket")
        # To make the math simpler, let's pretend our hash function can only
        # return 100 different values.
        with patch.object(Feature, "HASHSPACE", 100):
            # The feature is 100% rolled out and has two variants at 50% each. So,
            # the buckets are [0..50] and [51..100]. Mock the hash function to
            # return a value in the first bucket and then a value in the second.
            with patch("mmh3.hash128", side_effect=[33, 66]):
                assert feature.check_value(owner_id=123, default="c") == "first bucket"
                assert feature.check_value(owner_id=124, default="c") == "second bucket"

    def test_default_feature_flag_created(self):
        name = "my_default_feature"
        my_default_feature = Feature(name)

        my_default_feature.check_value(owner_id=123123123)

        feature_flag = FeatureFlag.objects.filter(name=name).first()

        assert feature_flag is not None
        assert feature_flag.proportion == 0

    def test_sync_feature_call(self):
        testing_feature = Feature("testing_dummy_feature")
        assert testing_feature.check_value(owner_id="hi", default=False) == False

    async def test_async_feature_call_fail(self):
        testing_feature = Feature("testing_dummy_feature")
        with self.assertRaises(SynchronousOnlyOperation):
            testing_feature.check_value(owner_id="hi", default=False) == False

    async def test_async_feature_call_success(self):
        testing_feature = Feature("testing_dummy_feature")
        await testing_feature.check_value_async(owner_id="hi", default=False) == False


class TestFeatureExposures(TestCase):
    def test_exposure_created(self):
        complex = FeatureFlag.objects.create(
            name="my_feature", proportion=1.0, salt="random_salt"
        )
        enabled = FeatureFlagVariant.objects.create(
            name="enabled", feature_flag=complex, proportion=1.0, value=True
        )
        FeatureFlagVariant.objects.create(
            name="disabled", feature_flag=complex, proportion=0, value=False
        )

        owner_id = 123123123

        my_feature = Feature("my_feature")
        my_feature.check_value(owner_id=owner_id)

        exposure = FeatureExposure.objects.all().first()

        assert exposure is not None
        assert exposure.owner == owner_id
        assert exposure.feature_flag == complex
        assert exposure.feature_flag_variant == enabled

    def test_exposure_not_created(self):
        complex = FeatureFlag.objects.create(
            name="my_feature", proportion=1.0, salt="random_salt"
        )
        FeatureFlagVariant.objects.create(
            name="enabled", feature_flag=complex, proportion=0, value=True
        )

        with patch.object(Feature, "create_exposure") as create_exposure:
            owner_id = 123123123

            my_feature = Feature("my_feature")
            my_feature.check_value(owner_id=owner_id)

            exposure = FeatureExposure.objects.first()

            # Should not create an exposure because the owner was not exposed to any
            # explicit variant, it was assigned the default behaviour
            assert exposure is None
            create_exposure.assert_not_called()
