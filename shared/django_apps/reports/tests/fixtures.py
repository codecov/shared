import pytest

from shared.django_apps.core.tests.factories import (
    RepositoryFactory,
)
from shared.django_apps.reports.models import Test, TestInstance
from shared.django_apps.reports.tests.factories import UploadFactory


@pytest.fixture
def repo_fixture():
    return RepositoryFactory()


@pytest.fixture
def upload_fixture():
    return UploadFactory()


@pytest.fixture
def create_upload_func():
    def create_upload():
        return UploadFactory()

    return create_upload


@pytest.fixture
def create_test_func(repo_fixture):
    test_i = 0

    def create_test():
        nonlocal test_i
        test_id = f"test_{test_i}"
        test = Test(
            id=test_id,
            repository=repo_fixture,
            testsuite="testsuite",
            name=f"test_{test_i}",
            flags_hash="",
        )
        test.save()
        test_i = test_i + 1

        return test

    return create_test


@pytest.fixture
def create_test_instance_func(repo_fixture, upload_fixture):
    def create_test_instance(
        test,
        outcome,
        commitid=None,
        branch=None,
        repoid=None,
        upload=upload_fixture,
        duration=0,
        created_at=None,
    ):
        ti = TestInstance(
            test=test,
            repoid=repo_fixture.repoid,
            outcome=outcome,
            upload=upload,
            duration_seconds=duration,
        )
        if created_at:
            ti.created_at = created_at
        if branch:
            ti.branch = branch
        if commitid:
            ti.commitid = commitid
        if repoid:
            ti.repoid = repoid
        ti.save()
        return ti

    return create_test_instance
