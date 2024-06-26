import enum

import factory
from factory.django import DjangoModelFactory
import datetime

from shared.django_apps.core.tests.factories import CommitFactory, RepositoryFactory
from shared.django_apps.reports import models
from shared.django_apps.reports.models import ReportResults, Flake, Test, TestInstance, ReducedError


# TODO: deduplicate this from graphql_api.types.enums
class UploadErrorEnum(enum.Enum):
    FILE_NOT_IN_STORAGE = "file_not_in_storage"
    REPORT_EXPIRED = "report_expired"
    REPORT_EMPTY = "report_empty"


class CommitReportFactory(DjangoModelFactory):
    class Meta:
        model = models.CommitReport

    commit = factory.SubFactory(CommitFactory)


class UploadFactory(DjangoModelFactory):
    class Meta:
        model = models.ReportSession

    build_code = factory.Sequence(lambda n: f"{n}")
    report = factory.SubFactory(CommitReportFactory)
    state = "processed"


class RepositoryFlagFactory(DjangoModelFactory):
    class Meta:
        model = models.RepositoryFlag

    repository = factory.SubFactory(RepositoryFactory)
    flag_name = factory.Faker("word")


class UploadFlagMembershipFactory(DjangoModelFactory):
    class Meta:
        model = models.UploadFlagMembership

    flag = factory.SubFactory(RepositoryFlagFactory)
    report_session = factory.SubFactory(UploadFactory)


class ReportLevelTotalsFactory(DjangoModelFactory):
    class Meta:
        model = models.ReportLevelTotals

    report = factory.SubFactory(CommitReportFactory)
    branches = factory.Faker("pyint")
    coverage = factory.Faker("pydecimal", min_value=10, max_value=90, right_digits=2)
    hits = factory.Faker("pyint")
    lines = factory.Faker("pyint")
    methods = factory.Faker("pyint")
    misses = factory.Faker("pyint")
    partials = factory.Faker("pyint")
    files = factory.Faker("pyint")


class UploadLevelTotalsFactory(DjangoModelFactory):
    class Meta:
        model = models.UploadLevelTotals

    report_session = factory.SubFactory(UploadFactory)


class ReportDetailsFactory(DjangoModelFactory):
    class Meta:
        model = models.ReportDetails

    report = factory.SubFactory(CommitReportFactory)
    _files_array = factory.LazyAttribute(lambda _: [])
    _files_array_storage_path = None


class UploadErrorFactory(DjangoModelFactory):
    class Meta:
        model = models.UploadError

    report_session = factory.SubFactory(UploadFactory)
    error_code = factory.Iterator(
        [
            UploadErrorEnum.FILE_NOT_IN_STORAGE,
            UploadErrorEnum.REPORT_EMPTY,
            UploadErrorEnum.REPORT_EXPIRED,
        ]
    )


class ReportResultsFactory(DjangoModelFactory):
    class Meta:
        model = ReportResults

    report = factory.SubFactory(CommitReportFactory)
    state = factory.Iterator(
        [
            ReportResults.ReportResultsStates.PENDING,
            ReportResults.ReportResultsStates.COMPLETED,
        ]
    )

class ReducedErrorFactory(DjangoModelFactory):
    class Meta:
        model = ReducedError

    message = factory.Sequence(lambda n: f"message_{n}")

class TestFactory(DjangoModelFactory):
    class Meta:
        model = Test

    repository = factory.SubFactory(RepositoryFactory)
    id = factory.Sequence(lambda n: f"test_{n}")


class TestInstanceFactory(DjangoModelFactory):
    class Meta:
        model = TestInstance

    test = factory.SubFactory(TestFactory)
    upload = factory.SubFactory(UploadFactory)
    duration_seconds = factory.Faker("pyint", min_value=0, max_value=1000)


class FlakeFactory(DjangoModelFactory):
    class Meta:
        model = Flake

    repository = factory.SubFactory(RepositoryFactory)
    test = factory.SubFactory(TestFactory)
    reduced_error = factory.SubFactory(ReducedErrorFactory)

    recent_passes_count = 0
    count = 0
    fail_count = 0
    start_date = datetime.datetime.now()
