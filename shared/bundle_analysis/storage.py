import tempfile
from enum import Enum
from typing import Optional

from shared.bundle_analysis.report import BundleAnalysisReport
from shared.config import get_config
from shared.storage.base import BaseStorageService
from shared.storage.exceptions import FileNotInStorageError


def get_bucket_name() -> str:
    return get_config("bundle_analysis", "bucket_name", default="bundle-analysis")


class StoragePaths(Enum):
    bundle_report = "v1/repos/{repo_key}/{report_key}/bundle_report.sqlite"
    upload = "v1/uploads/{upload_key}.json"

    def path(self, **kwargs):
        return self.value.format(**kwargs)


class BundleAnalysisReportLoader:
    """
    Loads and saves `BundleAnalysisReport`s into the underlying storage service.
    Requires a `repo_key` that uniquely and permanently (i.e. maybe not the name/slug)
    that identifies a repo in the storage layer.
    """

    def __init__(self, storage_service: BaseStorageService, repo_key: str):
        self.storage_service = storage_service
        self.repo_key = repo_key
        self.bucket_name = get_bucket_name()

    def load(self, report_key: str) -> Optional[BundleAnalysisReport]:
        """
        Loads the `BundleAnalysisReport` for the given report key from storage
        or returns `None` if no such report exists.
        """
        path = StoragePaths.bundle_report.path(
            repo_key=self.repo_key, report_key=report_key
        )
        _, db_path = tempfile.mkstemp()

        with open(db_path, "w+b") as f:
            try:
                self.storage_service.read_file(self.bucket_name, path, file_obj=f)
            except FileNotInStorageError:
                return None
        return BundleAnalysisReport(db_path)

    def save(self, report: BundleAnalysisReport, report_key: str):
        """
        Saves a `BundleAnalysisReport` for the given report key into storage.
        """
        storage_path = StoragePaths.bundle_report.path(
            repo_key=self.repo_key, report_key=report_key
        )
        with open(report.db_path, "rb") as f:
            self.storage_service.write_file(self.bucket_name, storage_path, f)
