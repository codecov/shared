# http://docs.celeryq.org/en/latest/configuration.html#configuration
from typing import Optional

from shared.config import get_config
from shared.utils.enums import TaskConfigGroup

# Task name follows the following convention:
# task_name |- app.<type>.<config_group>.<identifier>
# <type> can be "tasks" or "cron"
# <config_group> is the task's TaskConfigGroup
# <identifier> is the task name (usually same as task class)
sync_teams_task_name = f"app.tasks.{TaskConfigGroup.sync_teams.value}.SyncTeams"
sync_repos_task_name = f"app.tasks.{TaskConfigGroup.sync_repos.value}.SyncRepos"
delete_owner_task_name = f"app.tasks.{TaskConfigGroup.delete_owner.value}.DeleteOwner"
notify_task_name = f"app.tasks.{TaskConfigGroup.notify.value}.Notify"
pulls_task_name = f"app.tasks.{TaskConfigGroup.pulls.value}.Sync"
status_set_error_task_name = f"app.tasks.{TaskConfigGroup.status.value}.SetError"
status_set_pending_task_name = f"app.tasks.{TaskConfigGroup.status.value}.SetPending"
upload_task_name = f"app.tasks.{TaskConfigGroup.upload.value}.Upload"
upload_processor_task_name = f"app.tasks.{TaskConfigGroup.upload.value}.UploadProcessor"
upload_finisher_task_name = f"app.tasks.{TaskConfigGroup.upload.value}.UploadFinisher"
manual_upload_completion_trigger_task_name = (
    f"app.tasks.{TaskConfigGroup.upload.value}.ManualUploadCompletionTrigger"
)
archive_task_name = f"app.tasks.{TaskConfigGroup.archive.value}.MigrateToArchive"
bot_task_name = f"app.tasks.{TaskConfigGroup.verify_bot.value}.VerifyBot"
comment_task_name = f"app.tasks.{TaskConfigGroup.comment.value}.Comment"
flush_repo_task_name = f"app.tasks.{TaskConfigGroup.flush_repo.value}.FlushRepo"
ghm_sync_plans_task_name = f"app.tasks.{TaskConfigGroup.sync_plans.value}.SyncPlans"
send_email_task_name = f"app.tasks.{TaskConfigGroup.send_email.value}.SendEmail"
remove_webhook_task_name = (
    f"app.tasks.{TaskConfigGroup.remove_webhook.value}.RemoveOldHook"
)
synchronize_task_name = f"app.tasks.{TaskConfigGroup.synchronize.value}.Synchronize"
new_user_activated_task_name = (
    f"app.tasks.{TaskConfigGroup.new_user_activated.value}.NewUserActivated"
)
compute_comparison_task_name = (
    f"app.tasks.{TaskConfigGroup.compute_comparison.value}.ComputeComparison"
)
commit_update_task_name = (
    f"app.tasks.{TaskConfigGroup.commit_update.value}.CommitUpdate"
)

profiling_finding_task_name = (
    f"app.cron.{TaskConfigGroup.profiling.value}.findinguncollected"
)
profiling_summarization_task_name = (
    f"app.tasks.{TaskConfigGroup.profiling.value}.summarization"
)
profiling_collection_task_name = (
    f"app.tasks.{TaskConfigGroup.profiling.value}.collection"
)
profiling_normalization_task_name = (
    f"app.tasks.{TaskConfigGroup.profiling.value}.normalizer"
)

timeseries_backfill_task_name = f"app.tasks.{TaskConfigGroup.timeseries.value}.backfill"
timeseries_backfill_dataset_task_name = (
    f"app.tasks.{TaskConfigGroup.timeseries.value}.backfill_dataset"
)
timeseries_backfill_commits_task_name = (
    f"app.tasks.{TaskConfigGroup.timeseries.value}.backfill_commits"
)
timeseries_delete_task_name = f"app.tasks.{TaskConfigGroup.timeseries.value}.delete"

static_analysis_task_name = (
    f"app.tasks.{TaskConfigGroup.static_analysis.value}.check_suite"
)
label_analysis_task_name = (
    f"app.tasks.{TaskConfigGroup.label_analysis.value}.process_request"
)

health_check_task_name = f"app.cron.{TaskConfigGroup.healthcheck.value}.HealthCheckTask"
gh_app_webhook_check_task_name = (
    f"app.cron.{TaskConfigGroup.daily.value}.GitHubAppWebhooksCheckTask"
)
brolly_stats_rollup_task_name = (
    f"app.cron.{TaskConfigGroup.daily.value}.BrollyStatsRollupTask"
)


def get_task_group(task_name: str) -> Optional[str]:
    task_parts = task_name.split(".")
    if len(task_parts) != 4:
        return None
    return task_parts[2]


class BaseCeleryConfig(object):
    broker_url = get_config("services", "celery_broker") or get_config(
        "services", "redis_url"
    )
    result_backend = get_config("services", "celery_broker") or get_config(
        "services", "redis_url"
    )

    broker_transport_options = {"visibility_timeout": (60 * 60 * 6)}  # 6 hours
    result_extended = True
    task_default_queue = get_config(
        "setup", "tasks", "celery", "default_queue", default="celery"
    )
    health_check_default_queue = "healthcheck"

    # Import jobs
    imports = ("tasks",)

    task_serializer = "json"

    accept_content = ["json"]

    worker_max_memory_per_child = int(
        get_config(
            "setup", "tasks", "celery", "worker_max_memory_per_child", default=1500000
        )
    )  # 1.5GB

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
        get_config(
            "setup", "tasks", TaskConfigGroup.notify.value, "timeout", default=120
        )
    )
    timeseries_soft_time_limit = get_config(
        "setup",
        "tasks",
        TaskConfigGroup.timeseries.value,
        "soft_timelimit",
        default=400,
    )
    timeseries_hard_time_limit = get_config(
        "setup",
        "tasks",
        TaskConfigGroup.timeseries.value,
        "hard_timelimit",
        default=480,
    )

    gh_webhook_retry_soft_time_limit = get_config(
        "setup", "tasks", TaskConfigGroup.daily.value, "soft_timelimit", default=600
    )

    gh_webhook_retry_hard_time_limit = get_config(
        "setup", "tasks", TaskConfigGroup.daily.value, "hard_timelimit", default=680
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
        gh_app_webhook_check_task_name: {
            "soft_time_limit": gh_webhook_retry_soft_time_limit,
            "time_limit": gh_webhook_retry_hard_time_limit,
        },
    }

    task_routes = {
        sync_teams_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.sync_teams.value,
                "queue",
                default=task_default_queue,
            )
        },
        sync_repos_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.sync_repos.value,
                "queue",
                default=task_default_queue,
            )
        },
        delete_owner_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.delete_owner.value,
                "queue",
                default=task_default_queue,
            )
        },
        notify_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.notify.value,
                "queue",
                default=task_default_queue,
            )
        },
        pulls_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.pulls.value,
                "queue",
                default=task_default_queue,
            )
        },
        f"app.tasks.{TaskConfigGroup.status.value}.*": {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.status.value,
                "queue",
                default=task_default_queue,
            )
        },
        f"app.tasks.{TaskConfigGroup.upload.value}.*": {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.upload.value,
                "queue",
                default=task_default_queue,
            )
        },
        f"app.tasks.{TaskConfigGroup.archive.value}.*": {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.archive.value,
                "queue",
                default=task_default_queue,
            )
        },
        bot_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.verify_bot.value,
                "queue",
                default=task_default_queue,
            )
        },
        comment_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.comment.value,
                "queue",
                default=task_default_queue,
            )
        },
        flush_repo_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.flush_repo.value,
                "queue",
                default=task_default_queue,
            )
        },
        ghm_sync_plans_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.sync_plans.value,
                "queue",
                default=task_default_queue,
            )
        },
        remove_webhook_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.remove_webhook.value,
                "queue",
                default=task_default_queue,
            )
        },
        synchronize_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.synchronize.value,
                "queue",
                default=task_default_queue,
            )
        },
        new_user_activated_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.new_user_activated.value,
                "queue",
                default=task_default_queue,
            )
        },
        f"app.tasks.{TaskConfigGroup.profiling.value}.*": {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.profiling.value,
                "queue",
                default=task_default_queue,
            )
        },
        f"app.cron.{TaskConfigGroup.profiling.value}.*": {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.profiling.value,
                "queue",
                default=task_default_queue,
            )
        },
        commit_update_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.commit_update.value,
                "queue",
                default=task_default_queue,
            )
        },
        f"app.tasks.{TaskConfigGroup.timeseries.value}.*": {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.timeseries.value,
                "queue",
                default=task_default_queue,
            )
        },
        compute_comparison_task_name: {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.compute_comparison.value,
                "queue",
                default=task_default_queue,
            )
        },
        health_check_task_name: {
            "queue": health_check_default_queue,
        },
        f"app.tasks.{TaskConfigGroup.label_analysis.value}.*": {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.label_analysis.value,
                "queue",
                default=task_default_queue,
            )
        },
        f"app.tasks.{TaskConfigGroup.static_analysis.value}.*": {
            "queue": get_config(
                "setup",
                "tasks",
                TaskConfigGroup.static_analysis.value,
                "queue",
                default=task_default_queue,
            )
        },
    }
