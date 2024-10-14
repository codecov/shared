from typing import Literal, NotRequired, TypedDict


class ProviderAuthor(TypedDict):
    id: str | None
    username: str | None


class ProviderCommit(TypedDict):
    branch: str
    commitid: str
    slug: NotRequired[str]  # Only GitHub includes slug


class ProviderPull(TypedDict):
    author: ProviderAuthor
    base: ProviderCommit
    head: ProviderCommit
    state: Literal["open", "closed", "merged"]
    title: str
    id: str
    number: str
    labels: NotRequired[list[str]]  # Only GitHub includes labels
    merge_commit_sha: str | None
