import pytest

import shared.celery_config as celery_config
from shared.utils.enums import TaskConfigGroup


def test_celery_config():
    # NOTE: This test is fairly limited
    # Since all the fields get determined at import time (because they are class attributes),
    # it's not possibe to mock `get_config` in order to see their results here.
    # The only way to do so would to be to make each field a @classmethod
    # and hold the logic inside it.
    # It's not a terrible idea, but I am not sure of the impact of reloading those things every time
    # So the best we can do is to ensure the fields have a sane structure
    config = celery_config.BaseCeleryConfig
    assert hasattr(config, "broker_url")
    assert hasattr(config, "result_backend")
    assert hasattr(config, "task_default_queue")
    assert hasattr(config, "task_acks_late")
    assert hasattr(config, "worker_prefetch_multiplier")
    assert hasattr(config, "task_soft_time_limit")
    assert hasattr(config, "task_time_limit")
    assert hasattr(config, "notify_soft_time_limit")
    assert hasattr(config, "task_annotations")
    assert hasattr(config, "task_routes")
    assert hasattr(config, "worker_max_memory_per_child")
    assert sorted(config.task_routes.keys()) == [
        "app.cron.healthcheck.HealthCheckTask",
        "app.cron.profiling.*",
        "app.tasks.archive.*",
        "app.tasks.comment.Comment",
        "app.tasks.commit_update.CommitUpdate",
        "app.tasks.compute_comparison.ComputeComparison",
        "app.tasks.delete_owner.DeleteOwner",
        "app.tasks.flush_repo.FlushRepo",
        "app.tasks.label_analysis.*",
        "app.tasks.new_user_activated.NewUserActivated",
        "app.tasks.notify.Notify",
        "app.tasks.profiling.*",
        "app.tasks.pulls.Sync",
        "app.tasks.remove_webhook.RemoveOldHook",
        "app.tasks.static_analysis.*",
        "app.tasks.status.*",
        "app.tasks.sync_plans.SyncPlans",
        "app.tasks.sync_repo_languages.SyncLanguages",
        "app.tasks.sync_repo_languages_gql.SyncLanguagesGQL",
        "app.tasks.sync_repos.SyncRepos",
        "app.tasks.sync_teams.SyncTeams",
        "app.tasks.synchronize.Synchronize",
        "app.tasks.test_results.*",
        "app.tasks.timeseries.*",
        "app.tasks.upload.*",
        "app.tasks.verify_bot.VerifyBot",
    ]
    assert config.broker_transport_options == {"visibility_timeout": 21600}
    assert config.result_extended is True
    assert config.imports == ("tasks",)
    assert config.task_serializer == "json"
    assert config.accept_content == ["json"]
    assert config.worker_hijack_root_logger is False
    assert config.timezone == "UTC"
    assert config.enable_utc is True
    assert config.task_ignore_result is True
    assert config.worker_disable_rate_limits is True


@pytest.mark.parametrize(
    "task_name,task_group",
    [
        ("app.cron.healthcheck.HealthCheckTask", TaskConfigGroup.healthcheck.value),
        ("app.cron.profiling.findinguncollected", TaskConfigGroup.profiling.value),
        ("app.tasks.archive.MigrateToArchive", TaskConfigGroup.archive.value),
        ("app.tasks.verify_bot.VerifyBot", TaskConfigGroup.verify_bot.value),
        ("app.tasks.comment.Comment", TaskConfigGroup.comment.value),
        ("app.tasks.commit_update.CommitUpdate", TaskConfigGroup.commit_update.value),
        (
            "app.tasks.compute_comparison.ComputeComparison",
            TaskConfigGroup.compute_comparison.value,
        ),
        ("app.tasks.delete_owner.DeleteOwner", TaskConfigGroup.delete_owner.value),
        ("app.tasks.flush_repo.FlushRepo", TaskConfigGroup.flush_repo.value),
        ("app.tasks.sync_plans.SyncPlans", TaskConfigGroup.sync_plans.value),
        (
            "app.tasks.new_user_activated.NewUserActivated",
            TaskConfigGroup.new_user_activated.value,
        ),
        ("app.tasks.notify.Notify", TaskConfigGroup.notify.value),
        ("app.tasks.profiling.collection", TaskConfigGroup.profiling.value),
        ("app.tasks.profiling.normalizer", TaskConfigGroup.profiling.value),
        ("app.tasks.profiling.summarization", TaskConfigGroup.profiling.value),
        ("app.tasks.pulls.Sync", TaskConfigGroup.pulls.value),
        (
            "app.tasks.remove_webhook.RemoveOldHook",
            TaskConfigGroup.remove_webhook.value,
        ),
        ("app.tasks.status.SetError", TaskConfigGroup.status.value),
        ("app.tasks.status.SetPending", TaskConfigGroup.status.value),
        ("app.tasks.sync_repos.SyncRepos", TaskConfigGroup.sync_repos.value),
        (
            "app.tasks.sync_repo_languages.SyncLanguages",
            TaskConfigGroup.sync_repo_languages.value,
        ),
        (
            "app.tasks.sync_repo_languages_gql.SyncLanguagesGQL",
            TaskConfigGroup.sync_repo_languages_gql.value,
        ),
        ("app.tasks.sync_teams.SyncTeams", TaskConfigGroup.sync_teams.value),
        ("app.tasks.synchronize.Synchronize", TaskConfigGroup.synchronize.value),
        ("app.tasks.timeseries.backfill", TaskConfigGroup.timeseries.value),
        ("app.tasks.timeseries.backfill_commits", TaskConfigGroup.timeseries.value),
        ("app.tasks.timeseries.backfill_dataset", TaskConfigGroup.timeseries.value),
        ("app.tasks.timeseries.delete", TaskConfigGroup.timeseries.value),
        (
            "app.tasks.timeseries.save_commit_measurements",
            TaskConfigGroup.timeseries.value,
        ),
        ("app.tasks.upload.Upload", TaskConfigGroup.upload.value),
        ("app.tasks.upload.UploadProcessor", TaskConfigGroup.upload.value),
        ("app.tasks.upload.UploadFinisher", TaskConfigGroup.upload.value),
        (
            "app.tasks.static_analysis.check_suite",
            TaskConfigGroup.static_analysis.value,
        ),
        (
            "app.tasks.label_analysis.process_request",
            TaskConfigGroup.label_analysis.value,
        ),
        ("unknown.task", None),
        ("app.tasks.legacy", None),
    ],
)
def test_task_group(task_name, task_group):
    assert celery_config.get_task_group(task_name) == task_group
