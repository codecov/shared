import os
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

        # To make the math simpler, let's pretend our hash function can only
        # return 200 different values.
        with patch.object(Feature, "HASHSPACE", 200):

            complex_feature.check_value(owner_id=1234)  # to force fetch values from db

            # Because each feature variant has a proportion of 1/3, our three
            # buckets should be [0, 66], [66, 133], [133, 200]. However, our top-level
            # feature proportion is only 0.5, so each bucket size should be then
            # halved: [0, 33], [66, 99], [133, 166]

            buckets = complex_feature._buckets
            assert list(map(lambda x: (x[0], x[1]), buckets)) == [
                (0, 33),
                (66, 99),
                (133, 166),
            ]

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

    def test_override_no_proportion(self):
        overrides = FeatureFlag.objects.create(
            name="overrides_no_proportion", proportion=0, salt="random_salt"
        )
        FeatureFlagVariant.objects.create(
            name="single_variant",
            feature_flag=overrides,
            proportion=0,
            value=2,
            override_owner_ids=[321, 123],
        )

        feature = Feature("overrides_no_proportion")

        assert feature.check_value(owner_id=321, default=1) == 2
        assert feature.check_value(owner_id=123, default=1) == 2

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

    def test_rollout_proportion_changes_dont_affect_variant_assignments(self):
        my_feature_flag = FeatureFlag.objects.create(
            name="my_feature1", proportion=0.5, salt="random_salt"
        )
        FeatureFlagVariant.objects.create(
            name="var1", feature_flag=my_feature_flag, proportion=1 / 3, value=1
        )
        FeatureFlagVariant.objects.create(
            name="var2", feature_flag=my_feature_flag, proportion=1 / 3, value=2
        )
        FeatureFlagVariant.objects.create(
            name="var3", feature_flag=my_feature_flag, proportion=1 / 3, value=3
        )
        my_feature = Feature("my_feature1")

        # The purpose of this test is to ensure that even when the feature_flag proportion
        # changes, users assignments to variants never change. ie, if user `a` was ever assigned
        # to variant 1, then for any feature_flag proportion, user `a` will either be
        # assigned to variant 1, or is not participating in the rollout (default value).
        # https://github.com/codecov/engineering-team/issues/1515

        # To make the math simpler, let's pretend our hash function can only
        # return 200 different values.
        with patch.object(Feature, "HASHSPACE", 200):
            with patch("mmh3.hash128", side_effect=[30, 90, 150, 40, 30, 90, 150, 40]):
                a = my_feature.check_value(owner_id=123, default="c")
                b = my_feature.check_value(owner_id=124, default="c")
                c = my_feature.check_value(owner_id=125, default="c")
                d = my_feature.check_value(owner_id=126, default="d")

                assert a == 1
                assert b == 2
                assert c == 3
                assert d == "d"

                my_feature_flag.proportion = (
                    1.0  # buckets are now: [(0,66), (66, 133), (133, 200)]
                )
                my_feature_flag.save()

                my_feature._fetch_and_set_from_db.cache_clear()  # clear the TTL
                my_feature._fetch_and_set_from_db()  # refresh feature flag proportion and clear caches

                assert a == my_feature.check_value(owner_id=123, default="c")
                assert b == my_feature.check_value(owner_id=124, default="c")
                assert c == my_feature.check_value(owner_id=125, default="c")
                assert 1 == my_feature.check_value(
                    owner_id=126, default="d"
                )  # now in variant 1 since 40 \in (0,66)

    @patch.dict(os.environ, {"CODECOV__FEATURE__DISABLE": ""})
    def test_check_value_with_env_disable(self):
        feature = Feature("my_feature")
        with patch.object(feature, "_fetch_and_set_from_db") as fetch_fn:
            assert feature.check_value(owner_id=1, default=100) == 100
            fetch_fn.assert_not_called()
            assert not hasattr(feature.__dict__, "_buckets")

    @patch.dict(os.environ, {"CODECOV__FEATURE__NUM_FEATURE": "30"})
    @patch.dict(os.environ, {"CODECOV__FEATURE__STR_FEATURE": '"foo"'})
    @patch.dict(os.environ, {"CODECOV__FEATURE__NULL_FEATURE": "null"})
    def test_check_value_with_env_override(self):
        feature = Feature("num_feature")
        with patch.object(feature, "_fetch_and_set_from_db") as fetch_fn:
            assert feature.check_value(owner_id=1, default=100) == 30
            fetch_fn.assert_not_called()
            assert not hasattr(feature.__dict__, "_buckets")

        feature = Feature("str_feature")
        with patch.object(feature, "_fetch_and_set_from_db") as fetch_fn:
            assert feature.check_value(owner_id=1, default="bar") == "foo"
            fetch_fn.assert_not_called()
            assert not hasattr(feature.__dict__, "_buckets")

        feature = Feature("null_feature")
        with patch.object(feature, "_fetch_and_set_from_db") as fetch_fn:
            assert feature.check_value(owner_id=1, default=100) == None
            fetch_fn.assert_not_called()
            assert not hasattr(feature.__dict__, "_buckets")

    @patch.dict(os.environ, {"CODECOV__FEATURE__NUM_FEATURE": "30"})
    @patch.dict(os.environ, {"CODECOV__FEATURE__DISABLE": ""})
    def test_check_value_with_env_disable_and_env_override(self):
        feature = Feature("num_feature")
        with patch.object(feature, "_fetch_and_set_from_db") as fetch_fn:
            assert feature.check_value(owner_id=1, default=100) == 30
            fetch_fn.assert_not_called()
            assert not hasattr(feature.__dict__, "_buckets")

        feature = Feature("other_feature")
        with patch.object(feature, "_fetch_and_set_from_db") as fetch_fn:
            assert feature.check_value(owner_id=1, default=100) == 100
            fetch_fn.assert_not_called()
            assert not hasattr(feature.__dict__, "_buckets")


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
