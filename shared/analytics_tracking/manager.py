from shared.analytics_tracking.base import BaseAnalyticsTool
from shared.analytics_tracking.events import Events


class AnalyticsToolManager:

    BLANK_USER_ID = -1

    def __init__(self):
        self.tools = []

    def add_tool(self, tracking_tool: BaseAnalyticsTool):
        self.tools.append(tracking_tool)

    def remove_tool(self, tracking_tool: BaseAnalyticsTool):
        self.tools.remove(tracking_tool)

    def track_event(self, user_id, event_name, *, is_enterprise, event_data={}):
        for tool in self.tools:
            if tool.is_enabled():
                tool.track_event(
                    user_id,
                    event_name,
                    is_enterprise=is_enterprise,
                    event_data=event_data,
                )

    def track_user(self, user_id, user_data={}, is_enterprise=False):
        for tool in self.tools:
            if tool.is_enabled():
                tool.track_user(user_id, user_data, is_enterprise)

    def track_account_activated_repo_on_upload(
        self, repoid, ownerid, commitid, pullid, is_enterprise
    ):
        self.track_event(
            user_id=self.BLANK_USER_ID,
            event_name=Events.ACCOUNT_ACTIVATED_REPOSITORY_ON_UPLOAD.value,
            event_data={
                "repo_id": repoid,
                "repo_owner_id": ownerid,
                "commit_id": commitid,
                "pull_id": pullid,
            },
            is_enterprise=is_enterprise,
        )

    def track_account_activated_repo(
        self, repoid, ownerid, commitid, pullid, is_enterprise
    ):
        self.track_event(
            user_id=self.BLANK_USER_ID,
            event_name=Events.ACCOUNT_ACTIVATED_REPOSITORY.value,
            event_data={
                "repo_id": repoid,
                "repo_owner_id": ownerid,
                "commit_id": commitid,
                "pull_id": pullid,
            },
            is_enterprise=is_enterprise,
        )

    def track_account_uploaded_coverage_report(
        self, repoid, ownerid, commitid, pullid, is_enterprise
    ):
        self.track_event(
            user_id=self.BLANK_USER_ID,
            event_name=Events.ACCOUNT_UPLOADED_COVERAGE_REPORT.value,
            event_data={
                "repo_id": repoid,
                "repo_owner_id": ownerid,
                "commit_id": commitid,
                "pull_id": pullid,
            },
            is_enterprise=is_enterprise,
        )

    def track_user_signed_in(
        self, repoid, ownerid, commitid, pullid, is_enterprise, userid
    ):
        self.track_event(
            user_id=userid,
            event_name=Events.USER_SIGNED_IN.value,
            event_data={
                "repo_id": repoid,
                "repo_owner_id": ownerid,
                "commit_id": commitid,
                "pull_id": pullid,
            },
            is_enterprise=is_enterprise,
        )

    def track_user_signed_up(
        self, repoid, ownerid, commitid, pullid, is_enterprise, userid
    ):
        self.track_event(
            user_id=userid,
            event_name=Events.USER_SIGNED_UP.value,
            event_data={
                "repo_id": repoid,
                "repo_owner_id": ownerid,
                "commit_id": commitid,
                "pull_id": pullid,
            },
            is_enterprise=is_enterprise,
        )
