from typing import Dict, List, Optional, TypedDict, Union


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
    app_id: Optional[int] = None
    pem_path: Optional[str] = None


class TorngitInstanceData(TypedDict):
    owner: Union[OwnerInfo, Dict]
    repo: Union[RepoInfo, Dict]
    fallback_installations: List[Optional[GithubInstallationInfo]]
    installation: Optional[GithubInstallationInfo]
