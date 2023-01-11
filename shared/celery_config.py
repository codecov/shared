# http://docs.celeryq.org/en/latest/configuration.html#configuration
from shared.config import get_config

sync_teams_task_name = "app.tasks.sync_teams.SyncTeams"
sync_repos_task_name = "app.tasks.sync_repos.SyncRepos"
delete_owner_task_name = "app.tasks.delete_owner.DeleteOwner"
notify_task_name = "app.tasks.notify.Notify"
pulls_task_name = "app.tasks.pulls.Sync"
status_set_error_task_name = "app.tasks.status.SetError"
status_set_pending_task_name = "app.tasks.status.SetPending"
upload_task_name = "app.tasks.upload.Upload"
upload_processor_task_name = "app.tasks.upload_processor.UploadProcessorTask"
upload_finisher_task_name = "app.tasks.upload_finisher.UploadFinisherTask"
archive_task_name = "app.tasks.archive.MigrateToArchive"
bot_task_name = "app.tasks.bot.VerifyBot"
comment_task_name = "app.tasks.comment.Comment"
flush_repo_task_name = "app.tasks.flush_repo.FlushRepo"
ghm_sync_plans_task_name = "app.tasks.ghm_sync_plans.SyncPlans"
send_email_task_name = "app.tasks.send_email.SendEmail"
remove_webhook_task_name = "app.tasks.remove_webhook.RemoveOldHook"
synchronize_task_name = "app.tasks.synchronize.Synchronize"
new_user_activated_task_name = "app.tasks.new_user_activated.NewUserActivated"
add_to_sendgrid_list_task_name = "app.tasks.add_to_sendgrid_list.AddToSendgridList"
compute_comparison_task_name = "app.tasks.compute_comparison.ComputeComparison"
commit_update_task_name = "app.tasks.commit_update.CommitUpdate"

profiling_finding_task_name = "app.cron.profiling.findinguncollected"
profiling_summarization_task_name = "app.tasks.profiling.summarization"
profiling_collection_task_name = "app.tasks.profiling.collection"
profiling_normalization_task_name = "app.tasks.profiling.normalizer"

timeseries_backfill_task_name = "app.tasks.timeseries.backfill"
timeseries_backfill_dataset_task_name = "app.tasks.timeseries.backfill_dataset"
timeseries_backfill_commits_task_name = "app.tasks.timeseries.backfill_commits"

health_check_task_name = "app.cron.health_check.HealthCheckTask"
gh_app_webhook_check_task_name = "app.cron.daily.GitHubAppWebhooksCheckTask"


class BaseCeleryConfig(object):
    broker_url = get_config("services", "celery_broker") or get_config(
        "services", "redis_url"
    )
    result_backend = get_config("services", "celery_broker") or get_config(
        "services", "redis_url"
    )

    broker_transport_options = {"visibility_timeout": 60 * 60 * 5}  # 5 hours
    result_extended = True
    task_default_queue = get_config(
        "setup", "tasks", "celery", "default_queue", default="celery"
    )
    health_check_default_queue = "healthcheck"

    # Import jobs
    imports = ("tasks",)

    task_serializer = "json"

    accept_content = ["json"]

    worker_max_memory_per_child = 1500000  # 1.5GB

    # http://docs.celeryproject.org/en/latest/configuration.html?highlight=celery_redirect_stdouts#celeryd-hijack-root-logger
    worker_hijack_root_logger = False

    timezone = "UTC"
    enable_utc = True

    # http://docs.celeryproject.org/en/latest/configuration.html#celery-ignore-result
    task_ignore_result = True

    # http://celery.readthedocs.org/en/latest/userguide/tasks.html#disable-rate-limits-if-they-re-not-used
    worker_disable_rate_limits = True

    # http://celery.readthedocs.org/en/latest/faq.html#should-i-use-retry-or-acks-late
    task_acks_late = bool(get_config("setup", "tasks", "celery", "acks_late"))

    # http://celery.readthedocs.org/en/latest/userguide/optimizing.html#prefetch-limits
    worker_prefetch_multiplier = int(
        get_config("setup", "tasks", "celery", "prefetch", default=4)
    )
    # !!! NEVER 0 !!! 0 == infinate

    # http://celery.readthedocs.org/en/latest/configuration.html#celeryd-task-soft-time-limit
    task_soft_time_limit = int(
        get_config("setup", "tasks", "celery", "soft_timelimit", default=400)
    )

    # http://celery.readthedocs.org/en/latest/configuration.html#std:setting-CELERYD_TASK_TIME_LIMIT
    task_time_limit = int(
        get_config("setup", "tasks", "celery", "hard_timelimit", default=480)
    )

    notify_soft_time_limit = int(
        get_config("setup", "tasks", "notify", "timeout", default=60)
    )
    timeseries_soft_time_limit = get_config(
        "setup", "tasks", "timeseries", "soft_timelimit", default=400
    )
    timeseries_hard_time_limit = get_config(
        "setup", "tasks", "timeseries", "hard_timelimit", default=480
    )
    task_annotations = {
        delete_owner_task_name: {
            "soft_time_limit": 2 * task_soft_time_limit,
            "time_limit": 2 * task_time_limit,
        },
        notify_task_name: {
            "soft_time_limit": notify_soft_time_limit,
            "time_limit": notify_soft_time_limit + 20,
        },
        sync_repos_task_name: {
            "soft_time_limit": 2 * task_soft_time_limit,
            "time_limit": 2 * task_time_limit,
        },
        timeseries_backfill_dataset_task_name: {
            "soft_time_limit": timeseries_soft_time_limit,
            "time_limit": timeseries_hard_time_limit,
        },
        timeseries_backfill_commits_task_name: {
            "soft_time_limit": timeseries_soft_time_limit,
            "time_limit": timeseries_hard_time_limit,
        },
    }

    task_routes = {
        sync_teams_task_name: {
            "queue": get_config(
                "setup", "tasks", "sync_teams", "queue", default=task_default_queue
            )
        },
        sync_repos_task_name: {
            "queue": get_config(
                "setup", "tasks", "sync_repos", "queue", default=task_default_queue
            )
        },
        delete_owner_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                "delete_owner",
                "queue",
                default=task_default_queue,
            )
        },
        notify_task_name: {
            "queue": get_config(
                "setup", "tasks", "notify", "queue", default=task_default_queue
            )
        },
        pulls_task_name: {
            "queue": get_config(
                "setup", "tasks", "pulls", "queue", default=task_default_queue
            )
        },
        status_set_error_task_name: {
            "queue": get_config(
                "setup", "tasks", "status", "queue", default=task_default_queue
            )
        },
        status_set_pending_task_name: {
            "queue": get_config(
                "setup", "tasks", "status", "queue", default=task_default_queue
            )
        },
        upload_task_name: {
            "queue": get_config(
                "setup", "tasks", "upload", "queue", default=task_default_queue
            )
        },
        upload_processor_task_name: {
            "queue": get_config(
                "setup", "tasks", "upload", "queue", default=task_default_queue
            )
        },
        archive_task_name: {
            "queue": get_config(
                "setup", "tasks", "archive", "queue", default=task_default_queue
            )
        },
        bot_task_name: {
            "queue": get_config(
                "setup", "tasks", "verify_bot", "queue", default=task_default_queue
            )
        },
        comment_task_name: {
            "queue": get_config(
                "setup", "tasks", "comment", "queue", default=task_default_queue
            )
        },
        flush_repo_task_name: {
            "queue": get_config(
                "setup", "tasks", "flush_repo", "queue", default=task_default_queue
            )
        },
        ghm_sync_plans_task_name: {
            "queue": get_config(
                "setup", "tasks", "sync_plans", "queue", default=task_default_queue
            )
        },
        remove_webhook_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                "remove_webhook",
                "queue",
                default=task_default_queue,
            )
        },
        synchronize_task_name: {
            "queue": get_config(
                "setup", "tasks", "synchronize", "queue", default=task_default_queue
            )
        },
        new_user_activated_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                "new_user_activated",
                "queue",
                default=task_default_queue,
            )
        },
        profiling_finding_task_name: {
            "queue": get_config(
                "setup", "tasks", "profiling", "queue", default=task_default_queue
            )
        },
        profiling_summarization_task_name: {
            "queue": get_config(
                "setup", "tasks", "profiling", "queue", default=task_default_queue
            )
        },
        profiling_collection_task_name: {
            "queue": get_config(
                "setup", "tasks", "profiling", "queue", default=task_default_queue
            )
        },
        profiling_normalization_task_name: {
            "queue": get_config(
                "setup", "tasks", "profiling", "queue", default=task_default_queue
            )
        },
        commit_update_task_name: {
            "queue": get_config(
                "setup", "tasks", "commit_update", "queue", default=task_default_queue
            )
        },
        timeseries_backfill_task_name: {
            "queue": get_config(
                "setup", "tasks", "timeseries", "queue", default=task_default_queue
            )
        },
        timeseries_backfill_commits_task_name: {
            "queue": get_config(
                "setup", "tasks", "timeseries", "queue", default=task_default_queue
            )
        },
        timeseries_backfill_dataset_task_name: {
            "queue": get_config(
                "setup", "tasks", "timeseries", "queue", default=task_default_queue
            )
        },
        add_to_sendgrid_list_task_name: {"queue": task_default_queue},
        compute_comparison_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                "compute_comparison",
                "queue",
                default=task_default_queue,
            )
        },
        health_check_task_name: {
            "queue": health_check_default_queue,
        },
    }
