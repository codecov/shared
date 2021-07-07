import shared.celery_config


def test_celery_config():
    # NOTE: This test is fairly limited
    # Since all the fields get determined at import time (because they are class attributes),
    # it's not possibe to mock `get_config` in order to see their results here.
    # The only way to do so would to be to make each field a @classmethod
    # and hold the logic inside it.
    # It's not a terrible idea, but I am not sure of the impact of reloading those things every time
    # So the best we can do is to ensure the fields have a sane structure
    config = shared.celery_config.BaseCeleryConfig
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
        "app.tasks.add_to_sendgrid_list.AddToSendgridList",
        "app.tasks.archive.MigrateToArchive",
        "app.tasks.bot.VerifyBot",
        "app.tasks.comment.Comment",
        "app.tasks.compute_comparison.ComputeComparison",
        "app.tasks.delete_owner.DeleteOwner",
        "app.tasks.flush_repo.FlushRepo",
        "app.tasks.ghm_sync_plans.SyncPlans",
        "app.tasks.new_user_activated.NewUserActivated",
        "app.tasks.notify.Notify",
        "app.tasks.pulls.Sync",
        "app.tasks.remove_webhook.RemoveOldHook",
        "app.tasks.status.SetError",
        "app.tasks.status.SetPending",
        "app.tasks.sync_repos.SyncRepos",
        "app.tasks.sync_teams.SyncTeams",
        "app.tasks.synchronize.Synchronize",
        "app.tasks.upload.Upload",
        "app.tasks.upload_processor.UploadProcessorTask",
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
