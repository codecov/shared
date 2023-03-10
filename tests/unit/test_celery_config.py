import pytest

import shared.celery_config as celery_config


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
    assert sorted(config.task_routes.keys()) == [
        "app.cron.healthcheck.HealthCheckTask",
        "app.cron.profiling.*",
        "app.tasks.add_to_sendgrid_list.AddToSendgridList",
        "app.tasks.archive.MigrateToArchive",
        "app.tasks.comment.Comment",
        "app.tasks.commit_update.CommitUpdate",
        "app.tasks.compute_comparison.ComputeComparison",
        "app.tasks.delete_owner.DeleteOwner",
        "app.tasks.flush_repo.FlushRepo",
        "app.tasks.new_user_activated.NewUserActivated",
        "app.tasks.notify.Notify",
        "app.tasks.profiling.*",
        "app.tasks.pulls.Sync",
        "app.tasks.remove_webhook.RemoveOldHook",
        "app.tasks.status.*",
        "app.tasks.sync_plans.SyncPlans",
        "app.tasks.sync_repos.SyncRepos",
        "app.tasks.sync_teams.SyncTeams",
        "app.tasks.synchronize.Synchronize",
        "app.tasks.timeseries.*",
        "app.tasks.upload.*",
        "app.tasks.verify_bot.VerifyBot",
    ]
    assert config.broker_transport_options == {"visibility_timeout": 18000}
    assert config.result_extended is True
    assert config.imports == ("tasks",)
    assert config.task_serializer == "json"
    assert config.accept_content == ["json"]
    assert config.worker_max_memory_per_child == 1500000
    assert config.worker_hijack_root_logger is False
    assert config.timezone == "UTC"
    assert config.enable_utc is True
    assert config.task_ignore_result is True
    assert config.worker_disable_rate_limits is True


@pytest.mark.parametrize(
    "task_name,task_group",
    [
        ("app.cron.healthcheck.HealthCheckTask", "healthcheck"),
        ("app.cron.profiling.findinguncollected", "profiling"),
        ("app.tasks.add_to_sendgrid_list.AddToSendgridList", "add_to_sendgrid_list"),
        ("app.tasks.archive.MigrateToArchive", "archive"),
        ("app.tasks.verify_bot.VerifyBot", "verify_bot"),
        ("app.tasks.comment.Comment", "comment"),
        ("app.tasks.commit_update.CommitUpdate", "commit_update"),
        ("app.tasks.compute_comparison.ComputeComparison", "compute_comparison"),
        ("app.tasks.delete_owner.DeleteOwner", "delete_owner"),
        ("app.tasks.flush_repo.FlushRepo", "flush_repo"),
        ("app.tasks.sync_plans.SyncPlans", "sync_plans"),
        ("app.tasks.new_user_activated.NewUserActivated", "new_user_activated"),
        ("app.tasks.notify.Notify", "notify"),
        ("app.tasks.profiling.collection", "profiling"),
        ("app.tasks.profiling.normalizer", "profiling"),
        ("app.tasks.profiling.summarization", "profiling"),
        ("app.tasks.pulls.Sync", "pulls"),
        ("app.tasks.remove_webhook.RemoveOldHook", "remove_webhook"),
        ("app.tasks.status.SetError", "status"),
        ("app.tasks.status.SetPending", "status"),
        ("app.tasks.sync_repos.SyncRepos", "sync_repos"),
        ("app.tasks.sync_teams.SyncTeams", "sync_teams"),
        ("app.tasks.synchronize.Synchronize", "synchronize"),
        ("app.tasks.timeseries.backfill", "timeseries"),
        ("app.tasks.timeseries.backfill_commits", "timeseries"),
        ("app.tasks.timeseries.backfill_dataset", "timeseries"),
        ("app.tasks.timeseries.delete", "timeseries"),
        ("app.tasks.upload.Upload", "upload"),
        ("app.tasks.upload.UploadProcessor", "upload"),
        ("app.tasks.upload.UploadFinisher", "upload"),
        ("unknown.task", None),
        ("app.tasks.legacy", None),
    ],
)
def test_task_group(task_name, task_group):
    assert celery_config.get_task_group(task_name) == task_group
