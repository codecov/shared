from datetime import timedelta

from enum import Enum
from django.db.models import Q
from django.utils import timezone

from shared.django_apps.codecov_auth.models import Owner, TrialStatus
from shared.django_apps.core.models import Commit, Repository
from shared.django_apps.reports.models import ReportSession, ReportType
from shared.django_apps.user_measurements.models import UserMeasurement
from shared.plan.service import PlanService

class UploaderType(Enum):
    LEGACY="legacy"
    CLI="cli"


def query_monthly_coverage_measurements(plan_service: PlanService) -> int:
    owner = plan_service.current_org
    queryset = UserMeasurement.objects.filter(
        owner=owner,
        private_repo=True,
        created_at__gte=timezone.now() - timedelta(days=30),
        report_type="coverage",
    )
    if (
        plan_service.trial_status == TrialStatus.EXPIRED.value
        and plan_service.has_trial_dates
    ):
        queryset = queryset.filter(
            Q(created_at__gte=plan_service.trial_end_date)
            | Q(created_at__lte=plan_service.trial_start_date)
        )
    monthly_limit = plan_service.monthly_uploads_limit
    return queryset[:monthly_limit].count()


def insert_coverage_measurement(
    owner: Owner,
    repo: Repository,
    commit: Commit,
    upload: ReportSession,
    uploader_used: str,
    private_repo: bool,
    report_type: ReportType,
):
    return UserMeasurement.objects.create(
        repo=repo,
        commit=commit,
        upload=upload,
        owner=owner,
        uploader_used=uploader_used,
        private_repo=private_repo,
        report_type=report_type,
    )
