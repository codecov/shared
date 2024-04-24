from typing import Dict, List, TypedDict


class OwnerInfo(TypedDict):
    service_id: str
    ownerid: int | None
    username: str


class RepoInfo(TypedDict):
    name: str
    using_integration: bool
    service_id: str
    repoid: int
    private: bool | None


class GithubInstallationInfo(TypedDict):
    """Required info to get a token from Github for a given installation"""

    installation_id: int
    # The default app (configured via yaml) doesn't need this info.
    # All other apps need app_id and pem_path
    app_id: int | None = None
    pem_path: str | None = None


class TorngitInstanceData(TypedDict):
    owner: OwnerInfo | Dict
    repo: RepoInfo | Dict
    fallback_installations: List[GithubInstallationInfo] | None
    installation: GithubInstallationInfo | None
