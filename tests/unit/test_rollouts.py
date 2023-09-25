from shared.rollouts import Feature, FeatureVariant


class TestFeature(object):
    def test_buckets(self, mocker):
        complex_feature = Feature(
            "complex",
            0.5,
            variants={
                "a": FeatureVariant(1, 1 / 3),
                "b": FeatureVariant(2, 1 / 3),
                "c": FeatureVariant(3, 1 / 3),
            },
        )
        # To make the math simpler, let's pretend our hash function can only
        # return 200 different values.
        mocker.patch.object(Feature, "HASHSPACE", 200)

        # Because the top-level feature proportion is 0.5, we are only using the
        # first 50% of our 200 hash values as our test population: [0..100]
        # Each feature variant has a proportion of 1/3, so our three buckets
        # should be [0..33], [34..66], and [67..100]. Anything from [101..200]
        # is not part of the rollout yet.
        buckets = complex_feature._buckets
        assert list(map(lambda x: x[0], buckets)) == [33, 66, 100]

    def test_fully_rolled_out(self, mocker):
        # If the feature is 100% rolled out and only has one variant, then we
        # should skip the hashing and bucket stuff and just return the single
        # possible value.
        feature = Feature(
            "rolled_out", 1.0, variants={"enabled": FeatureVariant(True, 1.0)}
        )
        mock_buckets = mocker.patch.object(feature, "_buckets")

        assert feature.check_value("any", default=False) == True
        assert not mock_buckets.called

    def test_overrides(self, mocker):
        # If an identifier was manually opted into a specific variant, skip the
        # hashing and just return the value for that variant.
        feature = Feature(
            "overrides",
            1.0,
            variants={"a": FeatureVariant(1, 0.5), "b": FeatureVariant(2, 0.5)},
            overrides={"overridden": "b"},
        )
        mock_buckets = mocker.patch.object(feature, "_buckets")

        assert feature.check_value("overridden", default=1) == 2
        assert not mock_buckets.called

    def test_not_in_test_gets_default(self, mocker):
        feature = Feature(
            "not_in_test", 0.1, variants={"enabled": FeatureVariant(True, 1.0)}
        )
        # If the feature is only 10% rolled out, 2**128-1 is way past the end of
        # the test population and should get a default value back.
        mocker.patch("mmh3.hash128", return_value=2**128 - 1)

        assert feature.check_value("not in test", default="default") == "default"

    def test_return_values_for_each_bucket(self, mocker):
        feature = Feature(
            "return_values_for_each_bucket",
            1.0,
            variants={
                "a": FeatureVariant("first bucket", 0.5),
                "b": FeatureVariant("second bucket", 0.5),
            },
        )
        # To make the math simpler, let's pretend our hash function can only
        # return 100 different values.
        mocker.patch.object(Feature, "HASHSPACE", 100)

        # The feature is 100% rolled out and has two variants at 50% each. So,
        # the buckets are [0..50] and [51..100]. Mock the hash function to
        # return a value in the first bucket and then a value in the second.
        mocker.patch("mmh3.hash128", side_effect=[33, 66])

        assert feature.check_value("any1", default="c") == "first bucket"
        assert feature.check_value("any2", default="c") == "second bucket"
