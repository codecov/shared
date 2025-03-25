from datetime import datetime

import factory
import factory.fuzzy
from factory.django import DjangoModelFactory

from shared.django_apps.ta_timeseries import models


class TestrunFactory(DjangoModelFactory):
    class Meta:
        model = models.Testrun

    timestamp = datetime.now()
    test_id = factory.Sequence(lambda n: f"test_{n}".encode())
    name = factory.Sequence(lambda n: f"test_{n}")
    classname = factory.Sequence(lambda n: f"class_{n}")
    testsuite = factory.Sequence(lambda n: f"suite_{n}")
    computed_name = factory.Sequence(lambda n: f"computed_{n}")
    outcome = factory.fuzzy.FuzzyChoice(
        choices=["pass", "failure", "flaky_failure", "skip"]
    )
    duration_seconds = factory.fuzzy.FuzzyFloat(low=0.0, high=100.0)
    failure_message = factory.LazyAttribute(
        lambda obj: f"failure_message_{obj.outcome}"
        if obj.outcome == "failure"
        else None
    )
    framework = "Pytest"
    filename = factory.Sequence(lambda n: f"test_{n}.py")
    repo_id = 1
    commit_sha = "123"
    branch = "main"
    flags = []
    upload_id = 1
