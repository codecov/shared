from datetime import timedelta
from enum import Enum

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from shared.django_apps.codecov_auth.models import TrialStatus
from shared.django_apps.reports.models import ReportType
from shared.django_apps.user_measurements.models import UserMeasurement
from shared.plan.service import PlanService


class UploaderType(Enum):
    LEGACY = "legacy"
    CLI = "cli"


def query_monthly_coverage_measurements(plan_service: PlanService) -> int:
    owner_id = plan_service.current_org.ownerid
    queryset = UserMeasurement.objects.filter(
        owner_id=owner_id,
        private_repo=True,
        created_at__gte=timezone.now() - timedelta(days=30),
        report_type=ReportType.COVERAGE.value,
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


def bulk_insert_coverage_measurements(
    measurements: list[UserMeasurement],
) -> list[UserMeasurement]:
    """
    This function takes measurements as input and bulk_creates them into the DB.
    The atomic transaction ensures either all transactions are inserted or none
    if there's an error
    """
    with transaction.atomic():
        return UserMeasurement.objects.bulk_create(measurements)


def insert_coverage_measurement(
    owner_id: int,
    repo_id: int,
    commit_id: int,
    upload_id: int,
    uploader_used: str,
    private_repo: bool,
    report_type: ReportType,
):
    return UserMeasurement.objects.create(
        repo_id=repo_id,
        commit_id=commit_id,
        upload_id=upload_id,
        owner_id=owner_id,
        uploader_used=uploader_used,
        private_repo=private_repo,
        report_type=report_type,
    )
