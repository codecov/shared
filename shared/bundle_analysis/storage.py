from enum import Enum
from tempfile import NamedTemporaryFile
from typing import Optional

from shared.bundle_analysis.report import BundleReport
from shared.config import get_config
from shared.storage.base import BaseStorageService
from shared.storage.exceptions import FileNotInStorageError

BUCKET_NAME = get_config("bundle_analysis", "bucket_name", default="bundle-analysis")


class StoragePaths(Enum):
    bundle_report = "v1/repos/{repo_key}/{report_key}/bundle_report.sqlite"

    def path(self, **kwargs):
        return self.value.format(**kwargs)


class BundleReportLoader:
    """
    Loads and saves `BundleReport`s into the underlying storage service.
    Requires a `repo_key` that uniquely and permanently (i.e. maybe not the name/slug)
    that identifies a repo in the storage layer.
    """

    def __init__(self, storage_service: BaseStorageService, repo_key: str):
        self.storage_service = storage_service
        self.repo_key = repo_key

    def load(self, report_key: str) -> Optional[BundleReport]:
        """
        Loads the `BundleReport` for the given report key from storage
        or returns `None` if no such report exists.
        """
        path = StoragePaths.bundle_report.path(
            repo_key=self.repo_key, report_key=report_key
        )
        file = NamedTemporaryFile(mode="w+b", delete=False)

        try:
            self.storage_service.read_file(BUCKET_NAME, path, file_obj=file)
            bundle_report = BundleReport(file.name)
            return bundle_report
        except FileNotInStorageError:
            return None

    def save(self, bundle_report: BundleReport, report_key: str):
        """
        Saves a `BundleReport` for the given report key into storage.
        """
        storage_path = StoragePaths.bundle_report.path(
            repo_key=self.repo_key, report_key=report_key
        )
        with open(bundle_report.db_path, "rb") as f:
            self.storage_service.write_file(BUCKET_NAME, storage_path, f)
