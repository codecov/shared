from enum import Enum


class CodecovDatabaseEnum(Enum):
    @classmethod
    def choices(cls):
        return tuple((i.db_id, i.name) for i in cls)

    @classmethod
    def enum_from_int(cls, value):
        for elem in cls:
            if elem.db_id == value:
                return elem
        return None


class TaskConfigGroup(Enum):
    """
    Configuration Group for tasks.
    Marks the config key in the install yaml that affects a given task.
    """

    archive = "archive"
    cache_rollup = "cache_rollup"
    comment = "comment"
    commit_update = "commit_update"
    compute_comparison = "compute_comparison"
    daily = "daily"
    delete_owner = "delete_owner"
    flakes = "flakes"
    flush_repo = "flush_repo"
    healthcheck = "healthcheck"
    label_analysis = "label_analysis"
    new_user_activated = "new_user_activated"
    notify = "notify"
    profiling = "profiling"
    pulls = "pulls"
    remove_webhook = "remove_webhook"
    send_email = "send_email"
    static_analysis = "static_analysis"
    status = "status"
    sync_account = "sync_account"
    sync_plans = "sync_plans"
    sync_repos = "sync_repos"
    sync_teams = "sync_teams"
    sync_repo_languages = "sync_repo_languages"
    sync_repo_languages_gql = "sync_repo_languages_gql"
    synchronize = "synchronize"
    timeseries = "timeseries"
    upload = "upload"
    test_results = "test_results"
