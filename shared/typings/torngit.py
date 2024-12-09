from enum import Enum
from typing import Dict, List, Optional, TypedDict, Union

class UploadType(Enum):
    COVERAGE = "coverage"
    TEST_RESULTS = "test_results"
    BUNDLE_ANALYSIS = "bundle_analysis"

class OwnerInfo(TypedDict):
    service_id: str
    ownerid: Optional[int]
    username: str


class RepoInfo(TypedDict):
    name: str
    using_integration: bool
    service_id: str
    repoid: int
    private: Optional[bool]


class GithubInstallationInfo(TypedDict):
    """Required info to get a token from Github for a given installation"""

    id: int
    installation_id: int
    # The default app (configured via yaml) doesn't need this info.
    # All other apps need app_id and pem_path
    app_id: Optional[int]
    pem_path: Optional[str]

class AdditionalData(TypedDict):
    upload_type: Optional[UploadType]


class TorngitInstanceData(TypedDict):
    owner: Union[OwnerInfo, Dict]
    repo: Union[RepoInfo, Dict]
    fallback_installations: List[Optional[GithubInstallationInfo]] | None
    installation: Optional[GithubInstallationInfo]
    additional_data: Optional[AdditionalData]
