from django.test import TestCase

from shared.django_apps.reports.tests.factories import (
    RepositoryFlagFactory,
    UploadFactory,
    UploadFlagMembershipFactory,
)


class UploadTests(TestCase):
    def test_ci_url_when_no_provider(self):
        session = UploadFactory(provider=None)
        assert session.ci_url is None

    def test_ci_url_when_provider_do_not_have_build_url(self):
        session = UploadFactory(provider="azure_pipelines")
        assert session.ci_url is None

    def test_ci_url_when_provider_has_build_url(self):
        session = UploadFactory(provider="travis", job_code="123")
        repo = session.report.commit.repository
        assert (
            session.ci_url
            == f"https://travis-ci.com/{repo.author.username}/{repo.name}/jobs/{session.job_code}"
        )

    def test_ci_url_when_db_has_build_url(self):
        session = UploadFactory(build_url="http://example.com")
        assert session.ci_url == "http://example.com"

    def test_flags(self):
        session = UploadFactory()
        flag_one = RepositoryFlagFactory()
        flag_two = RepositoryFlagFactory()
        # connect the flag and membership
        UploadFlagMembershipFactory(flag=flag_one, report_session=session)
        UploadFlagMembershipFactory(flag=flag_two, report_session=session)

        assert (
            session.flag_names.sort() == [flag_one.flag_name, flag_two.flag_name].sort()
        )
