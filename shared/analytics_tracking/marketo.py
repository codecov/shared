import httpx

from shared.analytics_tracking.base import BaseAnalyticsTool
from shared.analytics_tracking.events import Event, Events
from shared.config import get_config

marketo_events = [
    Events.USER_SIGNED_IN.value,
    Events.USER_SIGNED_UP.value,
    Events.ACCOUNT_UPLOADED_COVERAGE_REPORT.value,
    Events.GDPR_OPT_IN.value,
]


class MarketoError(Exception):
    def __init__(self, error):
        self.code = error["code"]
        self.message = error["message"]

    def __str__(self):
        return f"MarketoError: {self.code} - {self.message}"


class Marketo(BaseAnalyticsTool):
    OAUTH_URL = "/identity/oauth/token"
    LEAD_URL = "/rest/v1/leads.json"

    def __init__(self) -> None:
        self.client_id = get_config("setup", "marketo", "client_id", default=None)
        self.client_secret = get_config(
            "setup", "marketo", "client_secret", default=None
        )
        self.base_url = get_config("setup", "marketo", "base_url", default=None)
        self.client = httpx.Client()

    @property
    def token(self):
        resp = self.retrieve_token()
        return resp["access_token"]

    @classmethod
    def is_enabled(cls):
        return bool(get_config("setup", "marketo", "enabled", default=False))

    def track_event(self, event: Event, *, is_enterprise, context: None):
        if event.name in marketo_events:
            body = {
                "input": [event.serialize()],
            }
            return self.make_rest_request(self.LEAD_URL, method="POST", json=body)

    def make_request(self, url, *args, **kwargs):
        full_url = self.base_url + url
        method = kwargs.pop("method", "GET")
        res = self.client.request(method, full_url, **kwargs)
        return res.json()

    def make_rest_request(self, url, *args, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        headers["Content-Type"] = "application/json"
        data = self.make_request(url, *args, headers=headers, **kwargs)

        if not data.get("success"):
            # just use the first error
            error = data["errors"][0]
            raise MarketoError(error)

        # we might have success=True but field level erros
        results = data.get("result", [])
        for result in results:
            if result.get("status") == "skipped":
                error = result["reasons"][0]
                raise MarketoError(error)
        return data

    def retrieve_token(self):
        url = f"{self.OAUTH_URL}?grant_type=client_credentials&client_id={self.client_id}&client_secret={self.client_secret}"
        return self.make_request(url)
