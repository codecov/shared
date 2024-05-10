import json
import logging
import os
from base64 import b64decode
from string import Template
from typing import List
from urllib.parse import quote, urlencode

import httpx

from shared.config import get_config
from shared.metrics import Counter, metrics
from shared.torngit.base import TokenType, TorngitBaseAdapter
from shared.torngit.enums import Endpoints
from shared.torngit.exceptions import (
    TorngitCantRefreshTokenError,
    TorngitClientError,
    TorngitClientGeneralError,
    TorngitObjectNotFoundError,
    TorngitRefreshTokenFailedError,
    TorngitServer5xxCodeError,
    TorngitServerUnreachableError,
)
from shared.torngit.status import Status
from shared.typings.oauth_token_types import OauthConsumerToken
from shared.utils.urls import url_concat

log = logging.getLogger(__name__)

METRICS_PREFIX = "services.torngit.gitlab"


GITLAB_API_CALL_COUNTER = Counter(
    "git_provider_api_calls_gitlab",
    "Number of times gitlab called this endpoint",
    ["endpoint"],
)


# Gitlab Enterprise uses the same urls as Gitlab, but has a separate Counter
GITLAB_E_API_CALL_COUNTER = Counter(
    "git_provider_api_calls_gitlab_enterprise",
    "Number of times gitlab enterprise called this endpoint",
    ["endpoint"],
)


GITLAB_API_ENDPOINTS = {
    "fetch_and_handle_errors_retry": {
        "counter": GITLAB_API_CALL_COUNTER.labels(
            endpoint="fetch_and_handle_errors_retry"
        ),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="fetch_and_handle_errors_retry"
        ),
        "url_template": "",  # no url template, just counter
    },
    "get_best_effort_branches": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_best_effort_branches"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_best_effort_branches"
        ),
        "url_template": Template(
            "/projects/${service_id}/repository/commits/${commit_sha}/refs?type=branch"
        ),
    },
    "get_ancestors_tree": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_ancestors_tree"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_ancestors_tree"
        ),
        "url_template": Template("/projects/${service_id}/repository/commits"),
    },
    "list_files": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="list_files"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="list_files"),
        "url_template": Template("/projects/${service_id}/repository/tree"),
    },
    "get_compare": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_compare"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="get_compare"),
        "url_template": Template(
            "/projects/${service_id}/repository/compare/?from=${base}&to=${head}"
        ),
    },
    "get_source": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_source"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="get_source"),
        "url_template": Template("/projects/${service_id}/repository/files/${path}"),
    },
    "get_repo_languages": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_repo_languages"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_repo_languages"
        ),
        "url_template": Template("/projects/${service_id}/languages"),
    },
    "get_repository_without_service_id": {
        "counter": GITLAB_API_CALL_COUNTER.labels(
            endpoint="get_repository_without_service_id"
        ),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_repository_without_service_id"
        ),
        "url_template": Template("/projects/${slug}"),
    },
    "get_repository_with_service_id": {
        "counter": GITLAB_API_CALL_COUNTER.labels(
            endpoint="get_repository_with_service_id"
        ),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_repository_with_service_id"
        ),
        "url_template": Template("/projects/${service_id}"),
    },
    "get_commit_diff": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_commit_diff"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_commit_diff"
        ),
        "url_template": Template(
            "/projects/${service_id}/repository/commits/${commit}/diff"
        ),
    },
    "get_is_admin": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_is_admin"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="get_is_admin"),
        "url_template": Template("/groups/${service_id}/members/all/${user_id}"),
    },
    "get_authenticated": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_authenticated"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_authenticated"
        ),
        "url_template": Template("/projects/${service_id}"),
    },
    "find_pull_request_with_commit": {
        "counter": GITLAB_API_CALL_COUNTER.labels(
            endpoint="find_pull_request_with_commit"
        ),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="find_pull_request_with_commit"
        ),
        "url_template": Template(
            "/projects/${service_id}/repository/commits/${commit}/merge_requests"
        ),
    },
    "find_pull_request": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="find_pull_request"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="find_pull_request"
        ),
        "url_template": Template(
            "/projects/${service_id}/merge_requests?state=${gitlab_state}"
        ),
    },
    "get_pull_requests": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_pull_requests"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_pull_requests"
        ),
        "url_template": Template(
            "/projects/${service_id}/merge_requests?state=${state}"
        ),
    },
    "get_branch": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_branch"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="get_branch"),
        "url_template": Template("/projects/${service_id}/repository/branches/${name}"),
    },
    "get_branches": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_branches"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="get_branches"),
        "url_template": Template("/projects/${service_id}/repository/branches"),
    },
    "get_pull_request_commits": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_pull_request_commits"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_pull_request_commits"
        ),
        "url_template": Template(
            "/projects/${service_id}/merge_requests/${pullid}/commits"
        ),
    },
    "get_commit": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_commit"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="get_commit"),
        "url_template": Template(
            "/projects/${service_id}/repository/commits/${commit}"
        ),
    },
    "get_authors": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_authors"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="get_authors"),
        "url_template": Template("/users"),
    },
    "delete_comment": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="delete_comment"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="delete_comment"
        ),
        "url_template": Template(
            "/projects/${service_id}/merge_requests/${pullid}/notes/${commentid}"
        ),
    },
    "edit_comment": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="edit_comment"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="edit_comment"),
        "url_template": Template(
            "/projects/${service_id}/merge_requests/${pullid}/notes/${commentid}"
        ),
    },
    "post_comment": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="post_comment"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="post_comment"),
        "url_template": Template(
            "/projects/${service_id}/merge_requests/${pullid}/notes"
        ),
    },
    "get_commit_statuses": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_commit_statuses"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_commit_statuses"
        ),
        "url_template": Template(
            "/projects/${service_id}/repository/commits/${commit}/statuses"
        ),
    },
    "set_commit_status": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="set_commit_status"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="set_commit_status"
        ),
        "url_template": Template("/projects/${service_id}/statuses/${commit}"),
    },
    "set_commit_status_merge_commit": {
        "counter": GITLAB_API_CALL_COUNTER.labels(
            endpoint="set_commit_status_merge_commit"
        ),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="set_commit_status_merge_commit"
        ),
        "url_template": Template("/projects/${service_id}/statuses/${merge_commit}"),
    },
    "get_pull_request_files": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_pull_request_files"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_pull_request_files"
        ),
        "url_template": Template(
            "/projects/${service_id}/merge_requests/${pullid}/diffs"
        ),
    },
    "get_pull_request": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_pull_request"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_pull_request"
        ),
        "url_template": Template("/projects/${service_id}/merge_requests/${pullid}"),
    },
    "get_pull_request_get_commits": {
        "counter": GITLAB_API_CALL_COUNTER.labels(
            endpoint="get_pull_request_get_commits"
        ),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_pull_request_get_commits"
        ),
        "url_template": Template(
            "/projects/${service_id}/merge_requests/${pullid}/commits"
        ),
    },
    "get_pull_request_get_parent": {
        "counter": GITLAB_API_CALL_COUNTER.labels(
            endpoint="get_pull_request_get_parent"
        ),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_pull_request_get_parent"
        ),
        "url_template": Template(
            "/projects/${service_id}/repository/commits/${first_commit}"
        ),
    },
    "list_repos_get_user": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="list_repos_get_user"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="list_repos_get_user"
        ),
        "url_template": Template("/user"),
    },
    "list_repos_get_groups": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="list_repos_get_groups"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="list_repos_get_groups"
        ),
        "url_template": Template("/groups/${username}"),
    },
    "list_repos_get_user_and_groups": {
        "counter": GITLAB_API_CALL_COUNTER.labels(
            endpoint="list_repos_get_user_and_groups"
        ),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="list_repos_get_user_and_groups"
        ),
        "url_template": Template("/groups?per_page=100"),
    },
    "list_repos_get_owned_projects": {
        "counter": GITLAB_API_CALL_COUNTER.labels(
            endpoint="list_repos_get_owned_projects"
        ),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="list_repos_get_owned_projects"
        ),
        "url_template": Template("/projects?owned=true&per_page=50&page=${page}"),
    },
    "list_repos_get_projects": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="list_repos_get_projects"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="list_repos_get_projects"
        ),
        "url_template": Template(
            "/groups/${group_id}/projects?per_page=50&page=${page}"
        ),
    },
    "get_owner_info_from_repo": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_owner_info_from_repo"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_owner_info_from_repo"
        ),
        "url_template": Template("/users?username=${username}"),
    },
    "delete_webhook": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="delete_webhook"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="delete_webhook"
        ),
        "url_template": Template("/projects/${service_id}/hooks/${hookid}"),
    },
    "edit_webhook": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="edit_webhook"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="edit_webhook"),
        "url_template": Template("/projects/${service_id}/hooks/${hookid}"),
    },
    "post_webhook": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="post_webhook"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="post_webhook"),
        "url_template": Template("/projects/${service_id}/hooks"),
    },
    "get_authenticated_user": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="get_authenticated_user"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="get_authenticated_user"
        ),
        "url_template": Template("/oauth/token"),
    },
    "refresh_token": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="refresh_token"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(
            endpoint="refresh_token"
        ),
        "url_template": Template("/oauth/token"),
    },
    "list_teams": {
        "counter": GITLAB_API_CALL_COUNTER.labels(endpoint="list_teams"),
        "enterprise_counter": GITLAB_E_API_CALL_COUNTER.labels(endpoint="list_teams"),
        "url_template": Template("/groups"),
    },
}

# uncounted urls
external_endpoint_template = Template("${username}/${name}/commit/${commitid}")


class Gitlab(TorngitBaseAdapter):
    service = "gitlab"
    service_url = "https://gitlab.com"
    api_url = "https://gitlab.com/api/v{}"

    @property
    def redirect_uri(self):
        from_config = get_config("gitlab", "redirect_uri", default=None)
        if from_config is not None:
            return from_config
        base = get_config("setup", "codecov_url", default="https://codecov.io")
        return base + "/login/gitlab"

    @classmethod
    def count_and_get_url_template(cls, url_name):
        GITLAB_API_ENDPOINTS[url_name]["counter"].inc()
        return GITLAB_API_ENDPOINTS[url_name]["url_template"]

    async def fetch_and_handle_errors(
        self,
        client,
        method,
        url_path,
        *,
        body=None,
        token: OauthConsumerToken = None,
        version=4,
        **args,
    ):
        if url_path.startswith("/"):
            _log = dict(
                event="api",
                endpoint=url_path,
                method=method,
                bot=(token or self.token).get("username"),
            )
            url_path = self.api_url.format(version) + url_path
        else:
            _log = {}

        headers = {
            "Accept": "application/json",
            "User-Agent": os.getenv("USER_AGENT", "Default"),
        }
        if isinstance(body, dict):
            headers["Content-Type"] = "application/json"
            body = json.dumps(body)
        url = url_concat(url_path, args).replace(" ", "%20")

        max_retries = 2
        for current_retry in range(1, max_retries + 1):
            if token or self.token:
                headers["Authorization"] = "Bearer %s" % (token or self.token)["key"]

            try:
                with metrics.timer(f"{METRICS_PREFIX}.api.run") as timer:
                    res = await client.request(
                        method.upper(), url, headers=headers, data=body
                    )
                    if current_retry > 1:
                        # count retries without getting a url
                        self.count_and_get_url_template("fetch_and_handle_errors_retry")
                logged_body = None
                if res.status_code >= 300 and res.text is not None:
                    logged_body = res.text
                log.log(
                    logging.WARNING if res.status_code >= 300 else logging.INFO,
                    "GitLab HTTP %s",
                    res.status_code,
                    extra=dict(time_taken=timer.ms, body=logged_body, **_log),
                )

                if res.status_code == 599:
                    metrics.incr(f"{METRICS_PREFIX}.api.unreachable")
                    raise TorngitServerUnreachableError(
                        "Gitlab was not able to be reached, server timed out."
                    )
                elif res.status_code >= 500:
                    metrics.incr(f"{METRICS_PREFIX}.api.5xx")
                    raise TorngitServer5xxCodeError("Gitlab is having 5xx issues")
                elif (
                    res.status_code == 401
                    and res.json().get("error") == "invalid_token"
                ):
                    # Refresh token and retry
                    log.debug("Token is invalid. Refreshing")
                    token = await self.refresh_token(client)
                    if callable(self._on_token_refresh):
                        await self._on_token_refresh(token)
                elif res.status_code >= 400:
                    message = f"Gitlab API: {res.status_code}"
                    metrics.incr(f"{METRICS_PREFIX}.api.clienterror")
                    raise TorngitClientGeneralError(
                        res.status_code, response_data=res.json(), message=message
                    )
                else:
                    # Success case
                    return res
            except (httpx.TimeoutException, httpx.NetworkError):
                metrics.incr(f"{METRICS_PREFIX}.api.unreachable")
                raise TorngitServerUnreachableError(
                    "GitLab was not able to be reached. Gateway 502. Please try again."
                )

    async def refresh_token(self, client: httpx.AsyncClient) -> OauthConsumerToken:
        """
        This function requests a refresh token from GitLab.
        The refresh_token value is stored as part of the oauth token dict.

        ! side effect: updates the self._token value
        ! raises TorngitCantRefreshTokenError
        ! raises TorngitRefreshTokenFailedError
        """
        creds_from_token = self._oauth_consumer_token()
        creds_to_send = dict(
            client_id=creds_from_token["key"], client_secret=creds_from_token["secret"]
        )

        if self.token.get("refresh_token") is None:
            raise TorngitCantRefreshTokenError(
                "Token doesn't have refresh token information"
            )

        # https://docs.gitlab.com/ee/api/oauth2.html#authorization-code-flow
        params = urlencode(
            dict(
                refresh_token=self.token["refresh_token"],
                grant_type="refresh_token",
                redirect_uri=self.redirect_uri,
                **creds_to_send,
            )
        )
        url = self.count_and_get_url_template("refresh_token").substitute()
        res = await client.request(
            "POST", self.service_url + url, data=params, params=params
        )
        if res.status_code >= 300:
            raise TorngitRefreshTokenFailedError(res)
        content = res.json()
        self.set_token(
            {
                "key": content["access_token"],
                "refresh_token": content["refresh_token"],
            }
        )
        return self.token

    async def api(self, method, url_path, *, body=None, token=None, version=4, **args):
        async with self.get_client() as client:
            res = await self.fetch_and_handle_errors(
                client, method, url_path, body=body, token=token, version=4, **args
            )
            return None if res.status_code == 204 else res.json()

    async def make_paginated_call(
        self,
        base_url,
        default_kwargs,
        max_per_page,
        counter_name,
        max_number_of_pages=None,
        token=None,
    ):
        current_page = None
        has_more = True
        count_so_far = 0

        async with self.get_client() as client:
            while has_more and (
                max_number_of_pages is None or count_so_far < max_number_of_pages
            ):
                current_kwargs = dict(per_page=max_per_page, **default_kwargs)
                if current_page is not None:
                    current_kwargs["page"] = current_page
                current_result = await self.fetch_and_handle_errors(
                    client, "GET", base_url, **current_kwargs
                )
                count_so_far += 1
                if count_so_far > 1:
                    # count calls after initial call
                    self.count_and_get_url_template(counter_name)
                yield (
                    None if current_result.status_code == 204 else current_result.json()
                )
                if (
                    max_number_of_pages is not None
                    and count_so_far >= max_number_of_pages
                ):
                    has_more = False
                elif current_result.headers.get("X-Next-Page"):
                    current_page, has_more = current_result.headers["X-Next-Page"], True
                else:
                    current_page, has_more = None, False

    async def get_authenticated_user(self, code, redirect_uri=None):
        """
        Gets access_token and user's details from gitlab.
        Exchanges the code for a proper access_token and refresh_token pair.
        Gets user details from /user endpoint from GitLab.
        Returns everything.

        Args:
            code: the code to be redeemed for an access_token / refresh_token pair
            redirect_uri: !deprecated. The uri to redirect to. Needs to match redirect_uri used to get the code.
        """
        creds_from_token = self._oauth_consumer_token()
        creds_to_send = dict(
            client_id=creds_from_token["key"], client_secret=creds_from_token["secret"]
        )
        redirect_uri = redirect_uri or self.redirect_uri
        url = self.count_and_get_url_template("get_authenticated_user").substitute()
        # http://doc.gitlab.com/ce/api/oauth2.html
        res = await self.api(
            "post",
            self.service_url + url,
            body=urlencode(
                dict(
                    code=code,
                    grant_type="authorization_code",
                    redirect_uri=redirect_uri,
                    **creds_to_send,
                )
            ),
        )

        self.set_token(
            {
                "key": res["access_token"],
                "refresh_token": res["refresh_token"],
            }
        )
        user = await self.api("get", "/user")
        user.update(res)
        return user

    async def post_webhook(self, name, url, events, secret, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.admin)
        # http://doc.gitlab.com/ce/api/projects.html#add-project-hook
        api_path = self.count_and_get_url_template("post_webhook").substitute(
            service_id=self.data["repo"]["service_id"]
        )
        res = await self.api(
            "post",
            api_path,
            body=dict(
                url=url,
                enable_ssl_verification=self.verify_ssl
                if isinstance(self.verify_ssl, bool)
                else True,
                token=secret,
                **events,
            ),
            token=token,
        )
        return res

    async def edit_webhook(self, hookid, name, url, events, secret, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.admin)
        # http://doc.gitlab.com/ce/api/projects.html#edit-project-hook
        api_path = self.count_and_get_url_template("edit_webhook").substitute(
            service_id=self.data["repo"]["service_id"], hookid=hookid
        )
        return await self.api(
            "put",
            api_path,
            body=dict(
                url=url,
                enable_ssl_verification=self.verify_ssl
                if type(self.verify_ssl) is bool
                else True,
                token=secret,
                **events,
            ),
            token=token,
        )

    async def delete_webhook(self, hookid, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.admin)
        # http://docs.gitlab.com/ce/api/projects.html#delete-project-hook
        url = self.count_and_get_url_template("delete_webhook").substitute(
            service_id=self.data["repo"]["service_id"], hookid=hookid
        )
        try:
            await self.api(
                "delete",
                url,
                token=token,
            )
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"Webhook with id {hookid} does not exist",
                )
            raise
        return True

    def diff_to_json(self, diff):
        if type(diff) is list:
            for d in diff:
                mode = ""
                if d["deleted_file"]:
                    mode = "deleted file mode\n"
                d["diff"] = (
                    ("diff --git a/%(old_path)s b/%(new_path)s\n" % d)
                    + mode
                    + d["diff"]
                )
            return super().diff_to_json("\n".join(map(lambda a: a["diff"], diff)))
        else:
            return super().diff_to_json(self, diff)

    async def get_owner_info_from_repo(self, repo, token=None):
        if repo.get("owner"):
            service_id = repo["owner"]["id"]
            username = repo["owner"]["username"].replace("/", ":")
        elif repo["namespace"]["kind"] == "user":
            # we need to get the user id (namespace id != user id)
            username = repo["namespace"]["path"]
            url = self.count_and_get_url_template(
                "get_owner_info_from_repo"
            ).substitute(username=username)
            user_info = await self.api("get", url, token=token)
            service_id = user_info[0].get("id") if user_info[0] else None
        elif repo["namespace"]["kind"] == "group":
            # we will use the namespace id as its the same as the group/subgroup id
            service_id = repo["namespace"]["id"]
            username = repo["namespace"]["full_path"].replace(
                "/", ":"
            )  # full path required for subgroup support
        else:
            raise

        return (service_id, username)

    async def list_repos(self, username=None, token=None):
        """
        V4 will return ALL projects, so we need to loop groups first
        """
        user_url = self.count_and_get_url_template("list_repos_get_user").substitute()
        user = await self.api("get", user_url, token=token)
        user["is_user"] = True
        if username:
            if username.lower() == user["username"].lower():
                # just me
                groups = [user]
            else:
                # a group
                groups_url = self.count_and_get_url_template(
                    "list_repos_get_groups"
                ).substitute(username=username)
                groups = [(await self.api("get", groups_url, token=token))]
        else:
            # user and all groups
            url = self.count_and_get_url_template(
                "list_repos_get_user_and_groups"
            ).substitute()
            groups = await self.api("get", url, token=token)
            groups.append(user)

        data = []
        for group in groups:
            page = 0
            while True:
                page += 1
                # http://doc.gitlab.com/ce/api/projects.html#projects
                if group.get("is_user"):
                    url = self.count_and_get_url_template(
                        "list_repos_get_owned_projects"
                    ).substitute(page=page)
                    repos = await self.api("get", url, token=token)
                else:
                    try:
                        url = self.count_and_get_url_template(
                            "list_repos_get_projects"
                        ).substitute(group_id=group["id"], page=page)
                        repos = await self.api("get", url, token=token)
                    except TorngitClientError as e:
                        if e.code == 404:
                            log.warning(f"Group with id {group['id']} does not exist")
                            repos = []
                for repo in repos:
                    (
                        owner_service_id,
                        owner_username,
                    ) = await self.get_owner_info_from_repo(repo, token)

                    # Gitlab API will return a repo with one of: no default branch key, default_branch: None, or default_branch: 'some_branch'
                    branch = "master"
                    if "default_branch" in repo and repo["default_branch"] is not None:
                        branch = repo.get("default_branch")
                    else:
                        log.warning(
                            "Repo doesn't have default_branch, using master instead",
                            extra=dict(repo=repo),
                        )

                    data.append(
                        dict(
                            owner=dict(
                                service_id=str(owner_service_id),
                                username=owner_username,
                            ),
                            repo=dict(
                                service_id=str(repo["id"]),
                                name=repo["path"],
                                private=(repo["visibility"] != "public"),
                                language=None,
                                branch=branch,
                            ),
                        )
                    )
                if len(repos) < 50:
                    break

        # deduplicate, since some of them might show up twice
        data = [i for n, i in enumerate(data) if i not in data[n + 1 :]]
        return data

    async def list_repos_generator(self, username=None, token=None):
        """
        Unlike GitHub and Bitbucket, GitLab has to pull a complete list of repos
        from multiple endpoints which can return overlapping results. We can
        still yield a page at a time through a generator to be consistent with
        the other providers, but we have to pre-fetch all of the pages to remove
        duplicates and then return slice after slice.
        """
        repos = await self.list_repos(username, token)
        page_size = 100
        for i in range(0, len(repos), page_size):
            yield repos[i : i + page_size]

    async def list_teams(self, token=None):
        # https://docs.gitlab.com/ce/api/groups.html#list-groups
        all_groups = []
        url = self.count_and_get_url_template("list_teams").substitute()
        async_generator = self.make_paginated_call(
            url,
            max_per_page=100,
            default_kwargs={},
            token=token,
            counter_name="list_teams",
        )
        async for page in async_generator:
            groups = page
            all_groups.extend(
                [
                    dict(
                        name=g["name"],
                        id=g["id"],
                        username=(g["full_path"].replace("/", ":")),
                        avatar_url=g["avatar_url"],
                        parent_id=g["parent_id"],
                    )
                    for g in groups
                ]
            )
        return all_groups

    async def get_pull_request(self, pullid, token=None):
        # https://docs.gitlab.com/ce/api/merge_requests.html#get-single-mr
        url = self.count_and_get_url_template("get_pull_request").substitute(
            service_id=self.data["repo"]["service_id"], pullid=pullid
        )
        try:
            pull = await self.api("get", url, token=token)
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"PR with id {pullid} does not exist",
                )
            raise

        if pull:
            if pull.get("diff_refs", {}) and pull.get("diff_refs", {}).get("base_sha"):
                parent = pull.get("diff_refs", {}).get("base_sha")
            else:
                log.info(
                    "Could not fetch pull base from diff_refs",
                    extra=dict(pullid=pullid, pull_information=pull),
                )
                # get list of commits and first one out
                url = self.count_and_get_url_template(
                    "get_pull_request_get_commits"
                ).substitute(service_id=self.data["repo"]["service_id"], pullid=pullid)
                all_commits = await self.api("get", url, token=token)
                log.info(
                    "List of commits is fetched for PR calculation",
                    extra=dict(
                        commit_list=[
                            {"id": c.get("id"), "parents": c.get("parent_ids")}
                            for c in all_commits
                        ]
                    ),
                )
                first_commit = all_commits[-1]
                if len(first_commit["parent_ids"]) > 0:
                    parent = first_commit["parent_ids"][0]
                else:
                    # try querying the parent commit for this parent
                    url = self.count_and_get_url_template(
                        "get_pull_request_get_parent"
                    ).substitute(
                        service_id=self.data["repo"]["service_id"],
                        first_commit=first_commit["id"],
                    )
                    parent = (await self.api("get", url, token=token))["parent_ids"][0]

            if pull["state"] == "locked":
                pull["state"] = "closed"

            return dict(
                author=dict(
                    id=str(pull["author"]["id"]) if pull["author"] else None,
                    username=pull["author"]["username"] if pull["author"] else None,
                ),
                base=dict(branch=pull["target_branch"] or "", commitid=parent),
                head=dict(branch=pull["source_branch"] or "", commitid=pull["sha"]),
                state="open"
                if pull["state"] in ("opened", "reopened")
                else pull["state"],
                title=pull["title"],
                id=str(pull["iid"]),
                number=str(pull["iid"]),
            )

    async def get_pull_request_files(self, pullid, token=None):
        # https://docs.gitlab.com/ee/api/merge_requests.html#list-merge-request-diffs
        url = self.count_and_get_url_template("get_pull_request_files").substitute(
            service_id=self.data["repo"]["service_id"], pullid=pullid
        )
        try:
            diffs = await self.api("get", url, token=token)
            filenames = [data.get("new_path") for data in diffs]
            return filenames
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"PR with id {pullid} does not exist",
                )
            raise

    async def set_commit_status(
        self,
        commit,
        status,
        context,
        description,
        url,
        coverage=None,
        merge_commit=None,
        token=None,
    ):
        token = self.get_token_by_type_if_none(token, TokenType.status)
        # https://docs.gitlab.com/ce/api/commits.html#post-the-build-status-to-a-commit
        status = dict(error="failed", failure="failed").get(status, status)
        api_path = self.count_and_get_url_template("set_commit_status").substitute(
            service_id=self.data["repo"]["service_id"], commit=commit
        )
        try:
            res = await self.api(
                "post",
                api_path,
                body=dict(
                    state=status,
                    target_url=url,
                    coverage=coverage,
                    name=context,
                    description=description,
                ),
                token=token,
            )
        except TorngitClientError:
            raise

        if merge_commit:
            api_path = self.count_and_get_url_template(
                "set_commit_status_merge_commit"
            ).substitute(
                service_id=self.data["repo"]["service_id"], merge_commit=merge_commit[0]
            )
            await self.api(
                "post",
                api_path,
                body=dict(
                    state=status,
                    target_url=url,
                    coverage=coverage,
                    name=merge_commit[1],
                    description=description,
                ),
                token=token,
            )
        return res

    async def get_commit_statuses(self, commit, _merge=None, token=None):
        # http://doc.gitlab.com/ce/api/commits.html#get-the-status-of-a-commit
        url = self.count_and_get_url_template("get_commit_statuses").substitute(
            service_id=self.data["repo"]["service_id"], commit=commit
        )
        statuses_response = await self.api("get", url, token=token)

        _states = dict(
            pending="pending",
            running="pending",
            success="success",
            error="failure",
            failed="failure",
            canceled="failure",
            created="pending",
            manual="pending",
            skipped="success",
            waiting_for_resource="pending",
            # These aren't on Github documentation but keeping here in case they're used somewhere
            # see https://github.com/codecov/shared/pull/30/ for context
            cancelled="failure",
            failure="failure",
        )
        statuses = [
            {
                "time": s.get("finished_at", s.get("created_at")),
                "state": _states.get(s["status"]),
                "description": s["description"],
                "url": s.get("target_url"),
                "context": s["name"],
            }
            for s in statuses_response
        ]

        for idx, status in enumerate(statuses):
            if status["time"] is None:
                log.warning(
                    "Set a None time on Gitlab commit status",
                    extra=dict(
                        commit=commit, status=status, gitlab_data=statuses_response[idx]
                    ),
                )
            if status["state"] is None:
                log.warning(
                    "Set a None state on Gitlab commit status",
                    extra=dict(
                        commit=commit, status=status, gitlab_data=statuses_response[idx]
                    ),
                )

        return Status(statuses)

    async def post_comment(self, pullid, body, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.comment)
        # http://doc.gitlab.com/ce/api/notes.html#create-new-merge-request-note
        url = self.count_and_get_url_template("post_comment").substitute(
            service_id=self.data["repo"]["service_id"], pullid=pullid
        )
        return await self.api("post", url, body=dict(body=body), token=token)

    async def edit_comment(self, pullid, commentid, body, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.comment)
        # http://doc.gitlab.com/ce/api/notes.html#modify-existing-merge-request-note
        url = self.count_and_get_url_template("edit_comment").substitute(
            service_id=self.data["repo"]["service_id"],
            pullid=pullid,
            commentid=commentid,
        )
        try:
            return await self.api("put", url, body=dict(body=body), token=token)
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"Comment {commentid} in PR {pullid} does not exist",
                )
            raise

    async def delete_comment(self, pullid, commentid, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.comment)
        # https://docs.gitlab.com/ce/api/notes.html#delete-a-merge-request-note
        url = self.count_and_get_url_template("delete_comment").substitute(
            service_id=self.data["repo"]["service_id"],
            pullid=pullid,
            commentid=commentid,
        )
        try:
            await self.api("delete", url, token=token)
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"Comment {commentid} in PR {pullid} does not exist",
                )
            raise
        return True

    async def get_commit(self, commit: str, token=None):
        # http://doc.gitlab.com/ce/api/commits.html#get-a-single-commit
        token = self.get_token_by_type_if_none(token, TokenType.read)
        url = self.count_and_get_url_template("get_commit").substitute(
            service_id=self.data["repo"]["service_id"], commit=commit
        )
        try:
            res = await self.api("get", url, token=token)
        except TorngitClientError as ce:
            if ce.code == 404:
                message = f"Commit {commit} not found in repo {self.data['repo']['service_id']}"
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data, message=message
                )
            raise
        # http://doc.gitlab.com/ce/api/users.html
        email = res["author_email"]
        name = res["author_name"]
        _id = None
        username = None
        url = self.count_and_get_url_template("get_authors").substitute()
        authors = await self.api("get", url, search=email or name, token=token)
        if authors:
            for author in authors:
                if author["name"] == name or author.get("email") == email:
                    _id = authors[0]["id"]
                    username = authors[0]["username"]
                    name = authors[0]["name"]
                    break

        return dict(
            author=dict(id=_id, username=username, email=email, name=name),
            message=res["message"],
            parents=res["parent_ids"],
            commitid=commit,
            timestamp=res["committed_date"],
        )

    async def get_pull_request_commits(self, pullid, token=None):
        # http://doc.gitlab.com/ce/api/merge_requests.html#get-single-mr-commits
        token = self.get_token_by_type_if_none(token, TokenType.read)
        url = self.count_and_get_url_template("get_pull_request_commits").substitute(
            service_id=self.data["repo"]["service_id"], pullid=pullid
        )
        commits = await self.api("get", url, token=token)
        return [c["id"] for c in commits]

    async def get_branches(self, token=None):
        # http://doc.gitlab.com/ce/api/projects.html#list-branches
        token = self.get_token_by_type_if_none(token, TokenType.read)
        url = self.count_and_get_url_template("get_branches").substitute(
            service_id=self.data["repo"]["service_id"]
        )
        res = await self.api("get", url, token=token)
        return [(b["name"], b["commit"]["id"]) for b in res]

    async def get_branch(self, name, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://docs.gitlab.com/ee/api/branches.html
        url = self.count_and_get_url_template("get_branch").substitute(
            service_id=self.data["repo"]["service_id"], name=name
        )
        branch = await self.api("get", url, token=token)
        return {"name": branch["name"], "sha": branch["commit"]["id"]}

    async def get_pull_requests(self, state="open", token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # ONLY searchable by branch.
        state = self.get_gitlab_pull_state_from_codecov_state(state=state)
        # [TODO] pagination coming soon
        # http://doc.gitlab.com/ce/api/merge_requests.html#list-merge-requests
        url = self.count_and_get_url_template("get_pull_requests").substitute(
            service_id=self.data["repo"]["service_id"], state=state
        )
        res = await self.api("get", url, token=token)
        # first check if the sha matches
        return [pull["iid"] for pull in res]

    def get_gitlab_pull_state_from_codecov_state(self, state):
        return {"merged": "merged", "open": "opened", "close": "closed"}.get(
            state, "all"
        )

    async def find_pull_request(
        self, commit=None, branch=None, state="open", token=None
    ):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        gitlab_state = self.get_gitlab_pull_state_from_codecov_state(state)
        if commit is not None:
            url = self.count_and_get_url_template(
                "find_pull_request_with_commit"
            ).substitute(service_id=self.data["repo"]["service_id"], commit=commit)
            try:
                res = await self.api("get", url, token=token)
                if len(res) > 1:
                    log.info("More than one pull request associated with commit")
                for possible_pull in res:
                    if possible_pull["state"] == gitlab_state or gitlab_state == "all":
                        return possible_pull["iid"]
            except TorngitClientError:
                log.warning("Unable to use new merge_requests endpoint")

        # [TODO] pagination coming soon
        # http://doc.gitlab.com/ce/api/merge_requests.html#list-merge-requests
        try:
            url = self.count_and_get_url_template("find_pull_request").substitute(
                service_id=self.data["repo"]["service_id"], gitlab_state=gitlab_state
            )
            res = await self.api("get", url, token=token)
        except TorngitClientError as e:
            if e.code == 403:
                # will get 403 if merge requests are disabled on gitlab
                return None
            raise

        # first check if the sha matches
        if commit:
            for pull in res:
                if pull["sha"] == commit:
                    log.info(
                        "Unable to find PR from new endpoint, found from old one",
                        extra=dict(commit=commit),
                    )
                    return pull["iid"]

        elif branch:
            for pull in res:
                if pull["source_branch"] and pull["source_branch"] == branch:
                    return pull["iid"]

        else:
            return res[0]["iid"]

    async def get_authenticated(self, token=None):
        # http://doc.gitlab.com/ce/api/projects.html#get-single-project
        # http://doc.gitlab.com/ce/permissions/permissions.html
        can_edit = False
        url = self.count_and_get_url_template("get_authenticated").substitute(
            service_id=self.data["repo"]["service_id"]
        )
        try:
            res = await self.api("get", url, token=token)
            permission = max(
                [
                    (res["permissions"]["group_access"] or {}).get("access_level") or 0,
                    (res["permissions"]["project_access"] or {}).get("access_level")
                    or 0,
                ]
            )
            can_edit = permission > 20
        except TorngitClientError:
            if self.data["repo"]["private"]:
                raise

        return (True, can_edit)

    async def get_is_admin(self, user, token=None):
        # https://docs.gitlab.com/ce/api/members.html#get-a-member-of-a-group-or-project-including-inherited-members
        # 10 = > Guest access
        # 20 = > Reporter access
        # 30 = > Developer access
        # 40 = > Maintainer access
        # 50 = > Owner access  # Only valid for groups
        user_id = int(user["service_id"])
        url = self.count_and_get_url_template("get_is_admin").substitute(
            service_id=self.data["owner"]["service_id"], user_id=user_id
        )
        res = await self.api("get", url, token=token)
        return bool(res["state"] == "active" and res["access_level"] > 39)

    async def get_commit_diff(self, commit, context=None, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # http://doc.gitlab.com/ce/api/commits.html#get-the-diff-of-a-commit
        url = self.count_and_get_url_template("get_commit_diff").substitute(
            service_id=self.data["repo"]["service_id"], commit=commit
        )
        res = await self.api("get", url, token=token)
        return self.diff_to_json(res)

    async def get_repository(self, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://docs.gitlab.com/ce/api/projects.html#get-single-project
        if self.data["repo"].get("service_id") is None:
            # convert from codecov ':' separator to gitlab '/' separator for groups/subgroups
            slug = self.slug.replace(":", "/")
            url = self.count_and_get_url_template(
                "get_repository_without_service_id"
            ).substitute(slug=slug.replace("/", "%2F"))
            res = await self.api("get", url, token=token)
        else:
            url = self.count_and_get_url_template(
                "get_repository_with_service_id"
            ).substitute(service_id=self.data["repo"]["service_id"])
            res = await self.api("get", url, token=token)

        owner_service_id, owner_username = await self.get_owner_info_from_repo(res)
        repo_name = res["path"]
        return dict(
            owner=dict(service_id=str(owner_service_id), username=owner_username),
            repo=dict(
                service_id=str(res["id"]),
                private=res["visibility"] != "public",
                language=None,
                branch=(res["default_branch"] or "master"),
                name=repo_name,
            ),
        )

    async def get_repo_languages(self, token=None) -> List[str]:
        """
        Gets the languages belonging to this repository.
        Reference:
            https://docs.gitlab.com/ee/api/projects.html#languages
        Returns:
            List[str]: A list of language names
        """
        token = self.get_token_by_type_if_none(token, TokenType.read)
        url = self.count_and_get_url_template("get_repo_languages").substitute(
            service_id=self.data["repo"]["service_id"]
        )
        res = await self.api("get", url, token=token)
        return list(k.lower() for k in res.keys())

    async def get_source(self, path, ref, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://docs.gitlab.com/ce/api/repository_files.html#get-file-from-repository
        url = self.count_and_get_url_template("get_source").substitute(
            service_id=self.data["repo"]["service_id"],
            path=urlencode(dict(a=path), quote_via=quote)[2:],
        )
        try:
            res = await self.api(
                "get",
                url,
                ref=ref,
                token=token,
            )
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"Path {path} not found at {ref}",
                )
            raise

        return dict(commitid=None, content=b64decode(res["content"]))

    async def get_compare(
        self, base, head, context=None, with_commits=True, token=None
    ):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://docs.gitlab.com/ee/api/repositories.html#compare-branches-tags-or-commits
        url = self.count_and_get_url_template("get_compare").substitute(
            service_id=self.data["repo"]["service_id"], base=base, head=head
        )
        compare = await self.api("get", url, token=token)

        return dict(
            diff=self.diff_to_json(compare["diffs"]),
            commits=[
                dict(
                    commitid=c["id"],
                    message=c["title"],
                    timestamp=c["created_at"],
                    author=dict(email=c["author_email"], name=c["author_name"]),
                )
                for c in compare["commits"]
            ][::-1],
        )

    async def list_top_level_files(self, ref, token=None):
        return await self.list_files(ref, dir_path="", token=None)

    async def list_files(self, ref, dir_path, token=None):
        # https://docs.gitlab.com/ee/api/repositories.html#list-repository-tree
        token = self.get_token_by_type_if_none(token, TokenType.read)
        url = self.count_and_get_url_template("list_files").substitute(
            service_id=self.data["repo"]["service_id"]
        )
        async_generator = self.make_paginated_call(
            base_url=url,
            default_kwargs=dict(ref=ref, path=dir_path),
            max_per_page=100,
            token=token,
            counter_name="list_files",
        )
        all_results = []
        async for page in async_generator:
            for res in page:
                if res["type"] == "blob":
                    res["type"] = "file"
                elif res["type"] == "tree":
                    res["type"] = "folder"
                else:
                    res["type"] = "other"
                all_results.append(res)
        return all_results

    async def get_ancestors_tree(self, commitid, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        url = self.count_and_get_url_template("get_ancestors_tree").substitute(
            service_id=self.data["repo"]["service_id"]
        )
        res = await self.api("get", url, token=token, ref_name=commitid)
        start = res[0]["id"]
        commit_mapping = {val["id"]: val["parent_ids"] for val in res}
        return self.build_tree_from_commits(start, commit_mapping)

    def get_external_endpoint(self, endpoint: Endpoints, **kwargs):
        # used in parent obj to get_href
        # I think this is for creating a clickable link,
        # not a token-using call by us, so not counting these calls.
        if endpoint == Endpoints.commit_detail:
            return external_endpoint_template.substitute(
                username=self.data["owner"]["username"].replace(":", "/"),
                name=self.data["repo"]["name"],
                commitid=kwargs["commitid"],
            )
        raise NotImplementedError()

    async def get_best_effort_branches(self, commit_sha: str, token=None) -> List[str]:
        """
        Gets a 'best effort' list of branches this commit is in.
        If a branch is returned, this means this commit is in that branch. If not, it could still be
            possible that this commit is in that branch
        Args:
            commit_sha (str): The sha of the commit we want to look at
        Returns:
            List[str]: A list of branch names
        """
        token = self.get_token_by_type_if_none(token, TokenType.read)
        url = self.count_and_get_url_template("get_best_effort_branches").substitute(
            service_id=self.data["repo"]["service_id"], commit_sha=commit_sha
        )
        async_generator = self.make_paginated_call(
            base_url=url,
            default_kwargs=dict(),
            max_per_page=100,
            token=token,
            counter_name="get_best_effort_branches",
        )
        all_results = []
        async for page in async_generator:
            for res in page:
                all_results.append(res["name"])
        return all_results

    async def is_student(self):
        return False
