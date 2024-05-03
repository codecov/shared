import base64
import hashlib
import logging
import os
from base64 import b64decode
from datetime import datetime, timezone
from string import Template
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlencode

import httpx
from httpx import Response

from shared.config import get_config
from shared.github import (
    get_github_integration_token,
    get_github_jwt_token,
    mark_installation_as_rate_limited,
)
from shared.metrics import Counter, metrics
from shared.torngit.base import TokenType, TorngitBaseAdapter
from shared.torngit.cache import get_redis_connection, torngit_cache
from shared.torngit.enums import Endpoints
from shared.torngit.exceptions import (
    TorngitClientError,
    TorngitClientGeneralError,
    TorngitMisconfiguredCredentials,
    TorngitObjectNotFoundError,
    TorngitRateLimitError,
    TorngitRefreshTokenFailedError,
    TorngitRepoNotFoundError,
    TorngitServer5xxCodeError,
    TorngitServerUnreachableError,
    TorngitUnauthorizedError,
)
from shared.torngit.status import Status
from shared.typings.oauth_token_types import OauthConsumerToken
from shared.typings.torngit import GithubInstallationInfo
from shared.utils.urls import url_concat

log = logging.getLogger(__name__)

METRICS_PREFIX = "services.torngit.github"


GITHUB_API_CALL_COUNTER = Counter(
    "git_provider_api_calls_github",
    "Number of times github called this endpoint",
    ["endpoint"],
)

# Github Enterprise uses the same urls as Github, but has a separate Counter
GITHUB_E_API_CALL_COUNTER = Counter(
    "git_provider_api_calls_github_enterprise",
    "Number of times github enterprise called this endpoint",
    ["endpoint"],
)


GITHUB_API_ENDPOINTS = {
    "request_webhook_redelivery": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="request_webhook_redelivery"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="request_webhook_redelivery"
        ),
        "url_template": Template("/app/hook/deliveries/${delivery_id}/attempts"),
    },
    "refresh_token": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="refresh_token"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="refresh_token"
        ),
        "url_template": Template("/login/oauth/access_token"),
    },
    "make_http_call_retry": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="make_http_call_retry"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="make_http_call_retry"
        ),
        "url_template": "",  # no url template, just counter
    },
    "list_webhook_deliveries": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="list_webhook_deliveries"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="list_webhook_deliveries"
        ),
        "url_template": Template("/app/hook/deliveries?per_page=50"),
    },
    "is_student": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="is_student"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(endpoint="is_student"),
        "url_template": Template("https://education.github.com/api/user"),
    },
    "get_best_effort_branches": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_best_effort_branches"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_best_effort_branches"
        ),
        "url_template": Template(
            "/repos/${slug}/commits/${commit_sha}/branches-where-head"
        ),
    },
    "get_workflow_run": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_workflow_run"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_workflow_run"
        ),
        "url_template": Template("/repos/${slug}/actions/runs/${run_id}"),
    },
    "update_check_run": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="update_check_run"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="update_check_run"
        ),
        "url_template": Template("/repos/${slug}/check-runs/${check_run_id}"),
    },
    "get_repos_with_languages_graphql": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="get_repos_with_languages_graphql"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_repos_with_languages_graphql"
        ),
        "url_template": Template("/graphql"),
    },
    "get_repo_languages": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_repo_languages"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_repo_languages"
        ),
        "url_template": Template("/repos/${slug}/languages"),
    },
    "get_check_suites": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_check_suites"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_check_suites"
        ),
        "url_template": Template("/repos/${slug}/commits/${git_sha}/check-suites"),
    },
    "create_check_run": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="create_check_run"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="create_check_run"
        ),
        "url_template": Template("/repos/${slug}/check-runs"),
    },
    "get_ancestors_tree": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_ancestors_tree"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_ancestors_tree"
        ),
        "url_template": Template("/repos/${slug}/commits"),
    },
    "list_files": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="list_files"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(endpoint="list_files"),
        "url_template": Template("/repos/${slug}/contents"),
    },
    "get_pull_request_files": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_pull_request_files"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_pull_request_files"
        ),
        "url_template": Template("/repos/${slug}/pulls/${pullid}/files"),
    },
    "find_pull_request": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="find_pull_request"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="find_pull_request"
        ),
        "url_template": Template("/repos/${slug}/commits/${commit}/pulls"),
    },
    "get_pull_requests": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_pull_requests"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_pull_requests"
        ),
        "url_template": Template("/repos/${slug}/pulls"),
    },
    "get_pull_request": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_pull_request"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_pull_request"
        ),
        "url_template": Template("/repos/${slug}/pulls/${pullid}"),
    },
    "get_distance_in_commits": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_distance_in_commits"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_distance_in_commits"
        ),
        "url_template": Template("/repos/${slug}/compare/${base_branch}...${base}"),
    },
    "get_compare": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_compare"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(endpoint="get_compare"),
        "url_template": Template("/repos/${slug}/compare/${base}...${head}"),
    },
    "get_commit_diff": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_commit_diff"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_commit_diff"
        ),
        "url_template": Template("/repos/${slug}/commits/${commit}"),
    },
    "get_source": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_source"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(endpoint="get_source"),
        "url_template": Template("/repos/${slug}/contents/${path}"),
    },
    "get_source_again": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_source_again"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_source_again"
        ),
        "url_template": "",  # no url template, just counter
    },
    "get_commit_statuses": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_commit_statuses"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_commit_statuses"
        ),
        "url_template": Template("/repos/${slug}/commits/${commit}/status"),
    },
    "set_commit_status": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="set_commit_status"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="set_commit_status"
        ),
        "url_template": Template("/repos/${slug}/statuses/${commit}"),
    },
    "set_commit_status_merge_commit": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="set_commit_status_merge_commit"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="set_commit_status_merge_commit"
        ),
        "url_template": Template("/repos/${slug}/statuses/${merge_commit}"),
    },
    "delete_comment": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="delete_comment"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="delete_comment"
        ),
        "url_template": Template("/repos/${slug}/issues/comments/${commentid}"),
    },
    "edit_comment": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="edit_comment"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(endpoint="edit_comment"),
        "url_template": Template("/repos/${slug}/issues/comments/${commentid}"),
    },
    "post_comment": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="post_comment"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(endpoint="post_comment"),
        "url_template": Template("/repos/${slug}/issues/${issueid}/comments"),
    },
    "delete_webhook": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="delete_webhook"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="delete_webhook"
        ),
        "url_template": Template("/repos/${slug}/hooks/${hookid}"),
    },
    "edit_webhook": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="edit_webhook"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(endpoint="edit_webhook"),
        "url_template": Template("/repos/${slug}/hooks/${hookid}"),
    },
    "post_webhook": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="post_webhook"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(endpoint="post_webhook"),
        "url_template": Template("/repos/${slug}/hooks"),
    },
    "get_raw_pull_request_commits": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="get_raw_pull_request_commits"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_raw_pull_request_commits"
        ),
        "url_template": Template(
            "/repos/${slug}/pulls/${pullid}/commits?per_page=${max}&page=${page_n}"
        ),
    },
    "list_teams": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="list_teams"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(endpoint="list_teams"),
        "url_template": Template("/user/memberships/orgs?state=active"),
    },
    "list_teams_org_name": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="list_teams_org_name"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="list_teams_org_name"
        ),
        "url_template": Template("/users/${login}"),
    },
    "get_gh_app_installation": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_gh_app_installation"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_gh_app_installation"
        ),
        "url_template": Template("/app/installations/${installation_id}"),
    },
    "get_repos_from_nodeids_generator_graphql": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="get_repos_from_nodeids_generator_graphql"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_repos_from_nodeids_generator_graphql"
        ),
        "url_template": Template("/graphql"),
    },
    "get_owner_from_nodeid_graphql": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="get_owner_from_nodeid_graphql"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_owner_from_nodeid_graphql"
        ),
        "url_template": Template("/graphql"),
    },
    "fetch_number_of_repos_graphql": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="fetch_number_of_repos_graphql"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="fetch_number_of_repos_graphql"
        ),
        "url_template": Template("/graphql"),
    },
    "fetch_page_of_repos_without_username": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="fetch_page_of_repos_without_username"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="fetch_page_of_repos_without_username"
        ),
        "url_template": Template("/user/repos?per_page=${page_size}&page=${page}"),
    },
    "fetch_page_of_repos_with_username": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="fetch_page_of_repos_with_username"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="fetch_page_of_repos_with_username"
        ),
        "url_template": Template(
            "/users/${username}/repos?per_page=${page_size}&page=${page}"
        ),
    },
    "fetch_page_of_repos_using_installation": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="fetch_page_of_repos_using_installation"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="fetch_page_of_repos_using_installation"
        ),
        "url_template": Template(
            "/installation/repositories?per_page=${page_size}&page=${page}"
        ),
    },
    "get_authenticated": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_authenticated"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_authenticated"
        ),
        "url_template": Template("/repos/${slug}"),
    },
    "get_is_admin": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_is_admin"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(endpoint="get_is_admin"),
        "url_template": Template(
            "/orgs/${owner_username}/memberships/${user_username}"
        ),
    },
    "get_user_token": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_user_token"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_user_token"
        ),
        "url_template": Template("/login/oauth/access_token"),
    },
    "get_authenticated_user": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_authenticated_user"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_authenticated_user"
        ),
        "url_template": Template("/user"),
    },
    "get_authenticated_user_email": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="get_authenticated_user_email"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_authenticated_user_email"
        ),
        "url_template": Template("/user/emails"),
    },
    "get_branch": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_branch"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(endpoint="get_branch"),
        "url_template": Template("/repos/${slug}/branches/${branch_name}"),
    },
    "get_branches": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="get_branches"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(endpoint="get_branches"),
        "url_template": Template("/repos/${slug}/branches"),
    },
    "get_repository_with_service_id": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="get_repository_with_service_id"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_repository_with_service_id"
        ),
        "url_template": Template("/repositories/${service_id}"),
    },
    "get_repository_without_service_id": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="get_repository_without_service_id"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_repository_without_service_id"
        ),
        "url_template": Template("/repos/${slug}"),
    },
    "get_check_runs_with_head_sha": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="get_check_runs_with_head_sha"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_check_runs_with_head_sha"
        ),
        "url_template": Template("/repos/${slug}/commits/${head_sha}/check-runs"),
    },
    "get_check_runs_with_check_suite_id": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="get_check_runs_with_check_suite_id"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_check_runs_with_check_suite_id"
        ),
        "url_template": Template(
            "/repos/${slug}/check-suites/${check_suite_id}/check-runs"
        ),
    },
    "list_files_with_dir_path": {
        "counter": GITHUB_API_CALL_COUNTER.labels(endpoint="list_files_with_dir_path"),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="list_files_with_dir_path"
        ),
        "url_template": Template("/repos/${slug}/contents/${dir_path}"),
    },
    "get_github_integration_token": {
        "counter": GITHUB_API_CALL_COUNTER.labels(
            endpoint="get_github_integration_token"
        ),
        "enterprise_counter": GITHUB_E_API_CALL_COUNTER.labels(
            endpoint="get_github_integration_token"
        ),
        "url_template": Template(
            "${api_endpoint}/app/installations/${integration_id}/access_tokens"
        ),
    },
}


# uncounted urls
external_endpoint_template = Template("${username}/${name}/commit/${commitid}")


class GitHubGraphQLQueries(object):
    _queries = dict(
        REPOS_FROM_NODEIDS="""
query GetReposFromNodeIds($node_ids: [ID!]!) {
    nodes(ids: $node_ids) {
        __typename 
        ... on Repository {
            # databaseId == service_id
            databaseId
            name
            primaryLanguage {
                name
            }
            isPrivate
            defaultBranchRef {
                name
            }
            owner {
                # This ID is actually the node_id, not the ownerid
                id
                login
            }
        }
    }
}
""",
        OWNER_FROM_NODEID="""
query GetOwnerFromNodeId($node_id: ID!) {
    node(id: $node_id) {
        __typename
        ... on Organization {
            login
            databaseId
        }
        ... on User {
            login
            databaseId
        }
    }
}
""",
        REPO_LANGUAGES_FROM_OWNER="""
query Repos($owner: String!, $cursor: String, $first: Int!) {
  repositoryOwner(login: $owner) {
    repositories(
      first: $first
      ownerAffiliations: OWNER
      isFork: false
      isLocked: false
      orderBy: {field: NAME, direction: ASC}
      after: $cursor
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        languages(first: 100) {
          edges {
            node {
              name
              id
            }
          }
        }
      }
    }
  }
}
""",
    )

    def get(self, query_name: str) -> Optional[str]:
        return self._queries.get(query_name, None)

    def prepare(self, query_name: str, variables: dict) -> Optional[dict]:
        # If Query was an object we could validate the variables
        query = self.get(query_name)
        if query is not None:
            return {"query": query, "variables": variables}


class Github(TorngitBaseAdapter):
    service = "github"
    graphql = GitHubGraphQLQueries()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._redis_connection = get_redis_connection()

    @classmethod
    def get_service_url(cls):
        return get_config("github", "url", default="https://github.com").strip("/")

    @property
    def service_url(self):
        return self.get_service_url()

    @classmethod
    def get_api_url(cls):
        return get_config("github", "api_url", default="https://api.github.com").strip(
            "/"
        )

    @property
    def api_url(self):
        return self.get_api_url()

    @classmethod
    def get_api_host_header(cls):
        return get_config(cls.service, "api_host_override")

    @property
    def api_host_header(self):
        return self.get_api_host_header()

    @classmethod
    def get_host_header(cls):
        return get_config(cls.service, "host_override")

    @property
    def host_header(self):
        return self.get_host_header()

    @property
    def token(self):
        return self._token

    @classmethod
    def count_and_get_url_template(cls, url_name):
        GITHUB_API_ENDPOINTS[url_name]["counter"].inc()
        return GITHUB_API_ENDPOINTS[url_name]["url_template"]

    async def api(self, *args, token=None, **kwargs):
        """
        Makes a single http request to GitHub and returns the parsed response
        """
        token_to_use = token or self.token

        log.info(
            "Making Github API call",
            extra=dict(
                has_token=bool(token),
                has_self_token=bool(self.token),
                is_same_token=(token == self.token),
            ),
        )

        if not token_to_use:
            raise TorngitMisconfiguredCredentials()
        response = await self.make_http_call(*args, token_to_use=token_to_use, **kwargs)
        return self._parse_response(response)

    async def paginated_api_generator(
        self, client, method, url_name, token=None, **kwargs
    ):
        """
        Generator that requests pages from GitHub and yields each page as they come.
        Continues to request pages while there's a link to the next page.
        """
        token_to_use = token or self.token
        if not token_to_use:
            raise TorngitMisconfiguredCredentials()
        url = self.count_and_get_url_template(
            url_name=url_name
        ).substitute()  # counts first call
        page = 1
        while url:
            args = [client, method, url]
            response = await self.make_http_call(
                *args, token_to_use=token_to_use, **kwargs
            )
            yield self._parse_response(response)
            url = response.links.get("next", {}).get("url", "")
            if page > 1:
                _ = self.count_and_get_url_template(
                    url_name=url_name
                ).substitute()  # counts subsequent calls
            page += 1

    def _parse_response(self, res: Response):
        if res.status_code == 204:
            return None
        elif res.headers.get("Content-Type")[:16] == "application/json":
            return res.json()
        else:
            try:
                return res.text
            except UnicodeDecodeError as uerror:
                log.warning(
                    "Unable to parse Github response",
                    extra=dict(
                        first_bytes=res.content[:100],
                        final_bytes=res.content[-100:],
                        errored_bytes=res.content[
                            (uerror.start - 10) : (uerror.start + 10)
                        ],
                        declared_contenttype=res.headers.get("content-type"),
                    ),
                )
                return res.text

    def _possibly_mark_current_installation_as_rate_limited(
        self,
        *,
        reset_timestamp: Optional[str] = None,
        retry_in_seconds: Optional[int] = None,
    ) -> None:
        current_installation = self.data.get("installation")
        if current_installation and current_installation.get("installation_id"):
            installation_id = current_installation["installation_id"]
            app_id = current_installation.get("app_id")
            if retry_in_seconds is None and reset_timestamp is None:
                log.warning(
                    "Can't mark installation as rate limited because TTL is missing",
                    extra=dict(installation_id=installation_id),
                )
                return
            ttl_seconds = retry_in_seconds
            if ttl_seconds is None:
                # https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api?apiVersion=2022-11-28#handle-rate-limit-errors-appropriately
                ttl_seconds = max(
                    0,
                    int(reset_timestamp) - int(datetime.now(timezone.utc).timestamp()),
                )
            if ttl_seconds > 0:
                log.info(
                    "Marking installation as rate limited",
                    extra=dict(
                        installation_id=installation_id,
                        app_id=app_id,
                        rate_limit_duration_seconds=ttl_seconds,
                    ),
                )
                mark_installation_as_rate_limited(
                    self._redis_connection, installation_id, ttl_seconds, app_id=app_id
                )

    def _get_next_fallback_token(
        self,
        *,
        reset_timestamp: Optional[str] = None,
        retry_in_seconds: Optional[int] = None,
    ) -> Optional[str]:
        """If additional fallback tokens were passed to this instance of GitHub
        select the next token in line to retry the previous request.

        !side effect: Marks the current token as rate limited in redis
        !side effect: Updates the self._token value
        !side effect: Consumes one of self.data.fallback_installations
        """
        fallback_installations: List[GithubInstallationInfo] = self.data.get(
            "fallback_installations", None
        )
        if fallback_installations is None or fallback_installations == []:
            # No tokens to fallback on
            return None
        # ! side effect: mark current token as rate limited
        self._possibly_mark_current_installation_as_rate_limited(
            reset_timestamp=reset_timestamp, retry_in_seconds=retry_in_seconds
        )
        # ! side effect: consume one of the fallback tokens (makes it the token of this instance)
        installation_info = fallback_installations.pop(0)
        # The function arg is 'integration_id'
        installation_id = installation_info.pop("installation_id")
        token_to_use = get_github_integration_token(
            self.service, installation_id, **installation_info
        )
        # ! side effect: update the token so subsequent requests won't fail
        self.set_token(dict(key=token_to_use))
        self.data["installation"] = {
            # Put the installation_id back into the info
            "installation_id": installation_id,
            **installation_info,
        }
        return token_to_use

    async def make_http_call(
        self,
        client,
        method,
        url,
        body=None,
        headers=None,
        token_to_use=None,
        statuses_to_retry=None,
        **args,
    ) -> Response:
        _headers = {
            "Accept": "application/json",
            "User-Agent": os.getenv("USER_AGENT", "Default"),
        }
        if token_to_use:
            _headers["Authorization"] = "token %s" % token_to_use["key"]
        _headers.update(headers or {})
        log_dict = {}

        method = (method or "GET").upper()
        if url[0] == "/":
            log_dict = dict(
                event="api",
                endpoint=url,
                method=method,
                bot=token_to_use.get("username"),
                repo_slug=self.slug,
                loggable_token=self.loggable_token(token_to_use),
            )
            url = self.api_url + url

        url = url_concat(url, args).replace(" ", "%20")

        if url.startswith(self.api_url) and self.api_host_header is not None:
            _headers["Host"] = self.api_host_header
        elif url.startswith(self.service_url) and self.host_header is not None:
            _headers["Host"] = self.host_header

        kwargs = dict(
            json=body if body else None, headers=_headers, follow_redirects=False
        )
        max_number_retries = 3
        tried_refresh = False
        for current_retry in range(1, max_number_retries + 1):
            retry_reason = "retriable_status"
            try:
                with metrics.timer(f"{METRICS_PREFIX}.api.run") as timer:
                    res = await client.request(method, url, **kwargs)
                    if current_retry > 1:
                        # count retries without getting a url
                        self.count_and_get_url_template(url_name="make_http_call_retry")
                logged_body = None
                if res.status_code >= 300 and res.text is not None:
                    logged_body = res.text
                log.log(
                    logging.WARNING if res.status_code >= 300 else logging.INFO,
                    "Github HTTP %s",
                    res.status_code,
                    extra=dict(
                        current_retry=current_retry,
                        time_taken=timer.ms,
                        body=logged_body,
                        rl_remaining=res.headers.get("X-RateLimit-Remaining"),
                        rl_limit=res.headers.get("X-RateLimit-Limit"),
                        rl_reset_time=res.headers.get("X-RateLimit-Reset"),
                        retry_after=res.headers.get("Retry-After"),
                        **log_dict,
                    ),
                )
            except (httpx.TimeoutException, httpx.NetworkError):
                metrics.incr(f"{METRICS_PREFIX}.api.unreachable")
                raise TorngitServerUnreachableError(
                    "GitHub was not able to be reached."
                )
            # Github doesn't have any specific message for trying to use an expired token
            # on top of that they return 404 for certain endpoints (not 401).
            # So this is the little heuristics that we follow to decide on refreshing a token
            if (
                # Only try to refresh once
                not tried_refresh
                # If there's no self._on_token_refresh then the token being used is probably from integration
                # and therefore can't be refreshed (i.e. it's not a user-to-server request)
                and callable(self._on_token_refresh)
                # Exclude the check to see if is_student from refreshes
                and url.startswith(self.api_url)
                # Requests that can potentially have failed due to token expired
                and (
                    (res.status_code == 401)
                    or (res.status_code == 404 and f"/repos/{self.slug}/" in url)
                )
            ):
                tried_refresh = True
                # Refresh token and retry
                log.debug("Token is invalid. Refreshing")
                token = await self.refresh_token(client, url)
                if token is not None:
                    # Assuming we could retry and the retry was successful
                    # Update headers and retry
                    prefix, _ = _headers["Authorization"].split(" ")
                    _headers["Authorization"] = f"{prefix} {token['key']}"
                    await self._on_token_refresh(token)
                    # Skip the rest of the validations and try again.
                    # It does consume one of the retries
                    retry_reason = "token_was_refreshed"
                    continue
            # Rate limit errors - we might fallback on other available tokens and retry
            # If we do fallback the token with rate limit is marked as 'rate limited' in Redis
            elif (res.status_code == 403 or res.status_code == 429) and (
                (
                    # Primary rate limit
                    int(res.headers.get("X-RateLimit-Remaining", -1)) == 0
                    or
                    # Secondary rate limit
                    res.headers.get("Retry-After") is not None
                )
            ):
                is_primary_rate_limit = (
                    int(res.headers.get("X-RateLimit-Remaining", -1)) == 0
                )
                metrics.incr(f"{METRICS_PREFIX}.api.ratelimiterror")
                reset_timestamp = res.headers.get("X-RateLimit-Reset")
                retry_after = res.headers.get("Retry-After")
                fallback_token_key = self._get_next_fallback_token(
                    reset_timestamp=reset_timestamp,
                    retry_in_seconds=(
                        int(retry_after) if retry_after is not None else None
                    ),
                )
                if fallback_token_key:
                    # Update header and try again
                    # Consumes one of the retries
                    prefix, _ = _headers["Authorization"].split(" ")
                    _headers["Authorization"] = f"{prefix} {fallback_token_key}"
                    retry_reason = "fallback_token_attempt"
                    continue
                else:
                    message = f"Github API rate limit error: {res.reason_phrase if is_primary_rate_limit else 'secondary rate limit'}"
                    raise TorngitRateLimitError(
                        response_data=res.text,
                        message=message,
                        reset=res.headers.get("X-RateLimit-Reset"),
                        retry_after=(
                            int(retry_after) if retry_after is not None else None
                        ),
                    )
            if (
                not statuses_to_retry
                or res.status_code not in statuses_to_retry
                or current_retry >= max_number_retries  # Last retry
            ):
                if res.status_code == 599:
                    metrics.incr(f"{METRICS_PREFIX}.api.unreachable")
                    raise TorngitServerUnreachableError(
                        "Github was not able to be reached, server timed out."
                    )
                elif res.status_code >= 500:
                    metrics.incr(f"{METRICS_PREFIX}.api.5xx")
                    raise TorngitServer5xxCodeError("Github is having 5xx issues")
                elif res.status_code == 401:
                    message = f"Github API unauthorized error: {res.reason_phrase}"
                    metrics.incr(f"{METRICS_PREFIX}.api.unauthorizederror")
                    raise TorngitUnauthorizedError(
                        response_data=res.text, message=message
                    )
                elif res.status_code >= 300:
                    message = f"Github API: {res.reason_phrase}"
                    metrics.incr(f"{METRICS_PREFIX}.api.clienterror")
                    raise TorngitClientGeneralError(
                        res.status_code, response_data=res.text, message=message
                    )
                return res
            else:
                log.info(
                    "Retrying request to GitHub",
                    extra=dict(
                        status=res.status_code, retry_reason=retry_reason, **log_dict
                    ),
                )

    async def refresh_token(
        self, client: httpx.AsyncClient, original_url: str
    ) -> Optional[OauthConsumerToken]:
        """
        This function requests a refresh token from Github.
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
            log.warning("Trying to refresh Github token with no refresh_token saved")
            return None

        # https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/refreshing-user-access-tokens#refreshing-a-user-access-token-with-a-refresh-token
        # Returns response as application/x-www-form-urlencoded
        params = urlencode(
            dict(
                refresh_token=self.token["refresh_token"],
                grant_type="refresh_token",
                **creds_to_send,
            )
        )
        url = (
            self.service_url
            + self.count_and_get_url_template(url_name="refresh_token").substitute()
        )
        res = await client.request(
            "POST",
            url,
            params=params,
        )
        if res.status_code >= 300:
            raise TorngitRefreshTokenFailedError(
                dict(
                    status_code=res.status_code,
                    response_text=res.text,
                    original_url=original_url,
                )
            )
        response_text = self._parse_response(res)
        session = parse_qs(response_text)

        if session.get("access_token"):
            self.set_token(
                {
                    # parse_qs put values in a list for reasons
                    "key": session["access_token"][0],
                    "refresh_token": session["refresh_token"][0],
                }
            )
            return self.token
        # https://docs.github.com/apps/managing-oauth-apps/troubleshooting-oauth-app-access-token-request-errors
        log.error(
            dict(
                error="No access_token in response",
                gh_error=session.get("error"),
                gh_error_description=session.get("error_description"),
            )
        )
        # Retunring None will let the code handle the request failure gracefully
        # Instead of probably throwing 500
        return None

    # Generic
    # -------
    async def get_branches(self, token=None):
        async with self.get_client() as client:
            token = self.get_token_by_type_if_none(token, TokenType.read)
            # https://developer.github.com/v3/repos/#list-branches
            page = 0
            branches = []
            while True:
                page += 1
                url = self.count_and_get_url_template(
                    url_name="get_branches"
                ).substitute(slug=self.slug)
                res = await self.api(
                    client,
                    "get",
                    url,
                    per_page=100,
                    page=page,
                    token=token,
                )
                if len(res) == 0:
                    break
                branches.extend([(b["name"], b["commit"]["sha"]) for b in res])
                if len(res) < 100:
                    break
            return branches

    async def get_branch(self, branch_name: str, token=None):
        async with self.get_client() as client:
            # https://docs.github.com/en/rest/branches/branches?apiVersion=2022-11-28#get-a-branch
            url = self.count_and_get_url_template(url_name="get_branch").substitute(
                slug=self.slug, branch_name=branch_name
            )
            res = await self.api(client, "get", url)
            return {"name": res["name"], "sha": res["commit"]["sha"]}

    async def get_authenticated_user(self, code):
        creds = self._oauth_consumer_token()
        async with self.get_client() as client:
            url = (
                self.service_url
                + self.count_and_get_url_template(
                    url_name="get_user_token"
                ).substitute()
            )
            response = await self.make_http_call(
                client,
                "get",
                url,
                code=code,
                client_id=creds["key"],
                client_secret=creds["secret"],
            )
            session = self._parse_response(response)

            if session.get("access_token"):
                # set current token
                self.set_token(
                    dict(
                        key=session["access_token"],
                        # Refresh token only exists if the app is configured
                        # to have expiring tokens
                        refresh_token=session.get("refresh_token", None),
                    )
                )
                url = self.count_and_get_url_template(
                    url_name="get_authenticated_user"
                ).substitute()
                user = await self.api(client, "get", url)
                user.update(session or {})
                email = user.get("email")
                url = self.count_and_get_url_template(
                    url_name="get_authenticated_user_email"
                ).substitute()
                if not email:
                    emails = await self.api(client, "get", url)
                    emails = [e["email"] for e in emails if e["primary"]]
                    user["email"] = emails[0] if emails else None
                return user

            else:
                if "error" in session:
                    # https://docs.github.com/en/apps/oauth-apps/maintaining-oauth-apps/troubleshooting-oauth-app-access-token-request-errors
                    log.error(
                        "Error fetching GitHub access token",
                        extra=dict(
                            error=session.get("error"),
                            error_description=session.get("error_description"),
                            error_uri=session.get("error_uri"),
                        ),
                    )
                return None

    async def get_is_admin(self, user, token=None):
        async with self.get_client() as client:
            # https://developer.github.com/v3/orgs/members/#get-organization-membership
            url = self.count_and_get_url_template(url_name="get_is_admin").substitute(
                owner_username=self.data["owner"]["username"],
                user_username=user["username"],
            )
            res = await self.api(client, "get", url, token=token)
            return res["state"] == "active" and res["role"] == "admin"

    async def get_authenticated(self, token=None):
        """Returns (can_view, can_edit)"""
        # https://developer.github.com/v3/repos/#get
        async with self.get_client() as client:
            url = self.count_and_get_url_template(
                url_name="get_authenticated"
            ).substitute(slug=self.slug)
            r = await self.api(client, "get", url, token=token)
            ok = r["permissions"]["admin"] or r["permissions"]["push"]
            return (True, ok)

    async def get_repository(self, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        async with self.get_client() as client:
            if self.data["repo"].get("service_id") is None:
                # https://developer.github.com/v3/repos/#get
                url = self.count_and_get_url_template(
                    url_name="get_repository_without_service_id"
                ).substitute(slug=self.slug)
                res = await self.api(client, "get", url, token=token)
            else:
                url = self.count_and_get_url_template(
                    url_name="get_repository_with_service_id"
                ).substitute(service_id=self.data["repo"]["service_id"])
                res = await self.api(client, "get", url, token=token)

        username, repo = tuple(res["full_name"].split("/", 1))
        parent = res.get("parent")

        if parent:
            fork = dict(
                owner=dict(
                    service_id=str(parent["owner"]["id"]),
                    username=parent["owner"]["login"],
                ),
                repo=dict(
                    service_id=str(parent["id"]),
                    name=parent["name"],
                    language=self._validate_language(parent["language"]),
                    private=parent["private"],
                    branch=parent["default_branch"],
                ),
            )
        else:
            fork = None

        return dict(
            owner=dict(service_id=str(res["owner"]["id"]), username=username),
            repo=dict(
                service_id=str(res["id"]),
                name=repo,
                language=self._validate_language(res["language"]),
                private=res["private"],
                fork=fork,
                branch=res["default_branch"] or "master",
            ),
        )

    def _process_repository_page(self, page):
        def process(repo):
            return dict(
                owner=dict(
                    service_id=str(repo["owner"]["id"]),
                    username=repo["owner"]["login"],
                ),
                repo=dict(
                    service_id=str(repo["id"]),
                    name=repo["name"],
                    language=self._validate_language(repo["language"]),
                    private=repo["private"],
                    branch=repo["default_branch"] or "master",
                ),
            )

        return list(map(process, page))

    async def _fetch_page_of_repos_using_installation(
        self, client, page_size=100, page=1
    ):
        # https://docs.github.com/en/rest/apps/installations?apiVersion=2022-11-28
        url = self.count_and_get_url_template(
            url_name="fetch_page_of_repos_using_installation"
        ).substitute(page_size=page_size, page=page)
        res = await self.api(
            client,
            "get",
            url,
            headers={"Accept": "application/vnd.github.machine-man-preview+json"},
        )

        repos = res.get("repositories", [])

        log.info(
            "Fetched page of repos using installation",
            extra=dict(
                page_size=page_size,
                page=page,
                repo_names=[repo["name"] for repo in repos] if len(repos) > 0 else [],
            ),
        )

        return self._process_repository_page(repos)

    async def _fetch_page_of_repos(
        self, client, username, token, page_size=100, page=1
    ):
        # https://developer.github.com/v3/repos/#list-your-repositories
        if username is None:
            url = self.count_and_get_url_template(
                url_name="fetch_page_of_repos_without_username"
            ).substitute(page_size=page_size, page=page)
            repos = await self.api(client, "get", url, token=token)
        else:
            url = self.count_and_get_url_template(
                url_name="fetch_page_of_repos_with_username"
            ).substitute(username=username, page_size=page_size, page=page)
            repos = await self.api(client, "get", url, token=token)

        log.info(
            "Fetched page of repos",
            extra=dict(
                page_size=page_size,
                page=page,
                repo_names=[repo["name"] for repo in repos] if len(repos) > 0 else [],
                username=username,
            ),
        )

        return self._process_repository_page(repos)

    async def _get_owner_from_nodeid(self, client, token, owner_node_id: str):
        query = self.graphql.prepare(
            "OWNER_FROM_NODEID", variables={"node_id": owner_node_id}
        )
        url = self.count_and_get_url_template(
            url_name="get_owner_from_nodeid_graphql"
        ).substitute()
        res = await self.api(client, "post", url, body=query, token=token)
        owner_data = res["data"]["node"]
        return {"username": owner_data["login"], "service_id": owner_data["databaseId"]}

    async def get_repos_from_nodeids_generator(
        self, repo_node_ids: List[str], expected_owner_username, *, token=None
    ):
        """Gets a list of repos from github graphQL API when the node_ids for the repos are known.
        Also gets the owner info (also from graphQL API) if the owner is not the expected one.
        The expected owner is one we are sure to have the info for available.

        Couldn't find how to use pagination with this endpoint, so we will implement it ourselves
        believing that the max number of node_ids we can use is 100.
        """
        token = self.get_token_by_type_if_none(token, TokenType.read)
        owners_seen = dict()
        async with self.get_client() as client:
            max_index = len(repo_node_ids)
            curr_index = 0
            PAGE_SIZE = 100
            while curr_index < max_index:
                chunk = repo_node_ids[curr_index : curr_index + PAGE_SIZE]
                curr_index += PAGE_SIZE
                query = self.graphql.prepare(
                    "REPOS_FROM_NODEIDS", variables={"node_ids": chunk}
                )
                url = self.count_and_get_url_template(
                    url_name="get_repos_from_nodeids_generator_graphql"
                ).substitute()
                res = await self.api(client, "post", url, body=query, token=token)
                for raw_repo_data in res["data"]["nodes"]:
                    if (
                        raw_repo_data is None
                        or raw_repo_data["__typename"] != "Repository"
                    ):
                        continue
                    primary_language = raw_repo_data.get("primaryLanguage")
                    default_branch = raw_repo_data.get("defaultBranchRef")
                    repo = {
                        "service_id": raw_repo_data["databaseId"],
                        "name": raw_repo_data["name"],
                        "language": self._validate_language(
                            primary_language.get("name") if primary_language else None
                        ),
                        "private": raw_repo_data["isPrivate"],
                        "branch": (
                            default_branch.get("name") if default_branch else None
                        ),
                        "owner": {
                            "node_id": raw_repo_data["owner"]["id"],
                            "username": raw_repo_data["owner"]["login"],
                        },
                    }
                    is_expected_owner = (
                        repo["owner"]["username"] == expected_owner_username
                    )
                    if not is_expected_owner:
                        ownerid = repo["owner"]["node_id"]
                        if ownerid not in owners_seen:
                            owner_info = await self._get_owner_from_nodeid(
                                client, token, ownerid
                            )
                            owners_seen[ownerid] = owner_info
                        repo["owner"] = {**repo["owner"], **owners_seen[ownerid]}

                    repo["owner"]["is_expected_owner"] = is_expected_owner
                    yield repo

    async def list_repos_using_installation(self, username=None):
        """
        returns list of repositories included in this integration
        """
        data = []
        page = 0
        async with self.get_client() as client:
            while True:
                page += 1
                repos = await self._fetch_page_of_repos_using_installation(
                    client, page=page
                )

                data.extend(repos)

                if len(repos) < 100:
                    break

            return data

    async def list_repos_using_installation_generator(self, username=None):
        """
        New version of list_repos_using_installation() that should replace the
        old one after safely rolling out in the worker.
        """
        async for page in self.list_repos_generator(
            username=username, using_installation=True
        ):
            yield page

    async def list_repos(self, username=None, token=None):
        """
        GitHub includes all visible repos through
        the same endpoint.
        """
        token = self.get_token_by_type_if_none(token, TokenType.read)
        page = 0
        data = []
        async with self.get_client() as client:
            while True:
                page += 1
                repos = await self._fetch_page_of_repos(
                    client, username, token, page=page
                )

                data.extend(repos)

                if len(repos) < 100:
                    break

            return data

    async def list_repos_generator(
        self, username=None, token=None, using_installation=False
    ):
        """
        New version of list_repos() that should replace the old one after safely
        rolling out in the worker.
        """
        token = self.get_token_by_type_if_none(token, TokenType.read)
        async with self.get_client() as client:
            page = 0
            while True:
                page += 1

                repos = (
                    await self._fetch_page_of_repos_using_installation(
                        client, page=page
                    )
                    if using_installation
                    else await self._fetch_page_of_repos(
                        client, username, token, page=page
                    )
                )

                yield repos

                if len(repos) < 100:
                    break

    # GH App Installation
    async def get_gh_app_installation(self, installation_id: int) -> Dict:
        """
        Gets gh app installation from the source.
        Reference:
            https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28#get-an-installation-for-the-authenticated-app
        Args:
            installation_id (int): Installation id belonging to the github app
        Returns:
            Dict: a dictionary that adheres to gh's response value in the link above
        """
        jwt_token = get_github_jwt_token(service=self.service)
        url = self.count_and_get_url_template(
            url_name="get_gh_app_installation"
        ).substitute(installation_id=installation_id)
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {jwt_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        async with self.get_client() as client:
            try:
                return await self.api(
                    client,
                    "get",
                    url,
                    token={"key": jwt_token},
                    headers=headers,
                )
            except TorngitClientError as ce:
                if ce.code == 404:
                    raise TorngitObjectNotFoundError(
                        response_data=ce.response_data,
                        message=f"Cannot find gh app with installation_id {installation_id}",
                    )
                raise

    async def list_teams(self, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.admin)
        # https://developer.github.com/v3/orgs/#list-your-organizations
        page, data = 0, []
        async with self.get_client() as client:
            while True:
                page += 1
                url = self.count_and_get_url_template(
                    url_name="list_teams"
                ).substitute()
                orgs = await self.api(client, "get", url, page=page, token=token)
                if len(orgs) == 0:
                    break
                # organization names
                for org in orgs:
                    try:
                        organization = org["organization"]
                        url = self.count_and_get_url_template(
                            url_name="list_teams_org_name"
                        ).substitute(login=organization["login"])
                        org = await self.api(client, "get", url, token=token)
                        data.append(
                            dict(
                                name=organization.get("name", org["login"]),
                                id=str(organization["id"]),
                                email=organization.get("email"),
                                username=organization["login"],
                            )
                        )
                    except TorngitClientGeneralError:
                        log.exception(
                            "Unable to load organization",
                            extra=dict(url=organization["url"]),
                        )
                if len(orgs) < 30:
                    break

            return data

    # Commits
    # -------
    async def get_pull_request_commits(self, pullid, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        commits = await self._get_raw_pull_request_commits(pullid, token)
        return [commit_info["sha"] for commit_info in commits]

    async def _get_raw_pull_request_commits(self, pullid, token):
        # https://developer.github.com/v3/pulls/#list-commits-on-a-pull-request
        # NOTE limited to 250 commits
        # NOTE page max size is 100
        # Which means we have to fetch at most 3 pages
        all_commits = []
        MAX_RESULTS_PER_PAGE = 100
        async with self.get_client() as client:
            for page_number in [1, 2, 3]:
                url = self.count_and_get_url_template(
                    url_name="get_raw_pull_request_commits"
                ).substitute(
                    slug=self.slug,
                    pullid=pullid,
                    max=MAX_RESULTS_PER_PAGE,
                    page_n=page_number,
                )
                page_results = await self.api(client, "get", url, token=token)
                if len(page_results):
                    all_commits.extend(page_results)
                if len(page_results) < MAX_RESULTS_PER_PAGE:
                    break
        return all_commits

    # Webhook
    # -------
    async def post_webhook(self, name, url, events, secret, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.admin)
        # https://developer.github.com/v3/repos/hooks/#create-a-hook
        async with self.get_client() as client:
            api_url = self.count_and_get_url_template(
                url_name="post_webhook"
            ).substitute(slug=self.slug)
            res = await self.api(
                client,
                "post",
                api_url,
                body=dict(
                    name="web",
                    active=True,
                    events=events,
                    config=dict(url=url, secret=secret, content_type="json"),
                ),
                token=token,
            )
            return res

    async def edit_webhook(self, hookid, name, url, events, secret, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.admin)
        # https://developer.github.com/v3/repos/hooks/#edit-a-hook
        try:
            async with self.get_client() as client:
                api_url = self.count_and_get_url_template(
                    url_name="edit_webhook"
                ).substitute(slug=self.slug, hookid=hookid)
                return await self.api(
                    client,
                    "patch",
                    api_url,
                    body=dict(
                        name="web",
                        active=True,
                        events=events,
                        config=dict(url=url, secret=secret, content_type="json"),
                    ),
                    token=token,
                )
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"Cannot find webhook {hookid}",
                )
            raise

    async def delete_webhook(self, hookid, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.admin)
        # https://developer.github.com/v3/repos/hooks/#delete-a-hook
        try:
            async with self.get_client() as client:
                url = self.count_and_get_url_template(
                    url_name="delete_webhook"
                ).substitute(slug=self.slug, hookid=hookid)
                await self.api(client, "delete", url, token=token)
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"Cannot find webhook {hookid}",
                )
            raise
        return True

    # Comments
    # --------
    async def post_comment(self, issueid, body, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.comment)
        # https://developer.github.com/v3/issues/comments/#create-a-comment
        async with self.get_client() as client:
            url = self.count_and_get_url_template(url_name="post_comment").substitute(
                slug=self.slug, issueid=issueid
            )
            res = await self.api(client, "post", url, body=dict(body=body), token=token)
            return res

    async def edit_comment(self, issueid, commentid, body, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.comment)
        # https://developer.github.com/v3/issues/comments/#edit-a-comment
        try:
            async with self.get_client() as client:
                url = self.count_and_get_url_template(
                    url_name="edit_comment"
                ).substitute(slug=self.slug, commentid=commentid)
                res = await self.api(
                    client, "patch", url, body=dict(body=body), token=token
                )
                return res
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"Cannot find comment {commentid} from PR {issueid}",
                )
            raise

    async def delete_comment(self, issueid, commentid, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.comment)
        # https://developer.github.com/v3/issues/comments/#delete-a-comment
        try:
            async with self.get_client() as client:
                url = self.count_and_get_url_template(
                    url_name="delete_comment"
                ).substitute(slug=self.slug, commentid=commentid)
                await self.api(client, "delete", url, token=token)
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"Cannot find comment {commentid} from PR {issueid}",
                )
            raise
        return True

    # Commit Status
    # -------------
    async def set_commit_status(
        self,
        commit,
        status,
        context,
        description,
        url,
        merge_commit=None,
        token=None,
        coverage=None,
    ):
        # https://developer.github.com/v3/repos/statuses
        token = self.get_token_by_type_if_none(token, TokenType.status)
        assert status in ("pending", "success", "error", "failure"), "status not valid"
        async with self.get_client() as client:
            try:
                api_url = self.count_and_get_url_template(
                    url_name="set_commit_status"
                ).substitute(slug=self.slug, commit=commit)
                res = await self.api(
                    client,
                    "post",
                    api_url,
                    body=dict(
                        state=status,
                        target_url=url,
                        context=context,
                        description=description,
                    ),
                    token=token,
                )
            except TorngitClientError as ce:
                raise
            if merge_commit:
                api_url = self.count_and_get_url_template(
                    url_name="set_commit_status_merge_commit"
                ).substitute(slug=self.slug, merge_commit=merge_commit[0])
                await self.api(
                    client,
                    "post",
                    api_url,
                    body=dict(
                        state=status,
                        target_url=url,
                        context=merge_commit[1],
                        description=description,
                    ),
                    token=token,
                )
            return res

    @torngit_cache.cache_function(
        torngit_cache.get_ttl("status"),
        log_hits=True,
        log_map={"args_indexes_to_log": [0], "kwargs_keys_to_log": ["commit"]},
    )
    async def get_commit_statuses(self, commit, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.status)
        page = 0
        statuses = []
        async with self.get_client() as client:
            while True:
                page += 1
                # https://developer.github.com/v3/repos/statuses/#list-statuses-for-a-specific-ref
                url = self.count_and_get_url_template(
                    url_name="get_commit_statuses"
                ).substitute(slug=self.slug, commit=commit)
                res = await self.api(
                    client,
                    "get",
                    url,
                    page=page,
                    per_page=100,
                    token=token,
                )
                provided_statuses = res.get("statuses", [])
                statuses.extend(
                    [
                        {
                            "time": s["updated_at"],
                            "state": s["state"],
                            "description": s["description"],
                            "url": s["target_url"],
                            "context": s["context"],
                        }
                        for s in provided_statuses
                    ]
                )
                if len(provided_statuses) < 100:
                    break
        return Status(statuses)

    # Source
    # ------
    async def get_source(self, path, ref, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://developer.github.com/v3/repos/contents/#get-contents
        try:
            async with self.get_client() as client:
                url = self.count_and_get_url_template(url_name="get_source").substitute(
                    slug=self.slug, path=path.replace(" ", "%20")
                )
                content = await self.api(client, "get", url, ref=ref, token=token)

                # When file size is greater than 1MB, content would not populate,
                # instead we have to retrieve it from the download_url
                if (
                    not content.get("content")
                    and content.get("download_url")
                    and content.get("encoding") == "none"
                ):
                    # not a templated url, count separately
                    self.count_and_get_url_template(url_name="get_source_again")
                    content["content"] = await self.api(
                        client=client, method="get", url=content["download_url"]
                    )
                else:
                    content["content"] = b64decode(content["content"])

        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"Path {path} not found at {ref}",
                )
            raise

        return dict(content=content["content"], commitid=content["sha"])

    async def get_commit_diff(self, commit, context=None, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        try:
            async with self.get_client() as client:
                url = self.count_and_get_url_template(
                    url_name="get_commit_diff"
                ).substitute(slug=self.slug, commit=commit)
                res = await self.api(
                    client,
                    "get",
                    url,
                    headers={"Accept": "application/vnd.github.v3.diff"},
                    token=token,
                )
        except TorngitClientError as ce:
            if ce.code == 422:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"Commit with id {commit} does not exist",
                )
            raise
        return self.diff_to_json(res)

    @torngit_cache.cache_function(
        torngit_cache.get_ttl("compare"),
        log_hits=True,
        log_map={"args_indexes_to_log": [0, 1], "kwargs_keys_to_log": ["base", "head"]},
    )
    async def get_compare(
        self, base, head, context=None, with_commits=True, token=None
    ):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://developer.github.com/v3/repos/commits/#compare-two-commits
        async with self.get_client() as client:
            url = self.count_and_get_url_template(url_name="get_compare").substitute(
                slug=self.slug, base=base, head=head
            )
            res = await self.api(client, "get", url, token=token)
        files = {}
        for f in res["files"]:
            diff = self.diff_to_json(
                "diff --git a/%s b/%s%s\n%s\n%s\n%s"
                % (
                    f.get("previous_filename") or f.get("filename"),
                    f.get("filename"),
                    (
                        "\ndeleted file mode 100644"
                        if f["status"] == "removed"
                        else "\nnew file mode 100644"
                        if f["status"] == "added"
                        else ""
                    ),
                    "--- "
                    + (
                        "/dev/null"
                        if f["status"] == "new"
                        else ("a/" + f.get("previous_filename", f.get("filename")))
                    ),
                    "+++ "
                    + (
                        "/dev/null"
                        if f["status"] == "removed"
                        else ("b/" + f["filename"])
                    ),
                    f.get("patch", ""),
                )
            )
            files.update(diff["files"])

        # commits are returned in reverse chronological order. ie [newest...oldest]
        return dict(
            diff=dict(files=files),
            commits=[
                dict(
                    commitid=c["sha"],
                    message=c["commit"]["message"],
                    timestamp=c["commit"]["author"]["date"],
                    author=dict(
                        id=(c["author"] or {}).get("id"),
                        username=(c["author"] or {}).get("login"),
                        name=c["commit"]["author"]["name"],
                        email=c["commit"]["author"]["email"],
                    ),
                )
                for c in ([res["base_commit"]] + res["commits"])
            ][::-1],
        )

    async def get_distance_in_commits(
        self, base_branch, base, context=None, with_commits=True, token=None
    ):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://developer.github.com/v3/repos/commits/#compare-two-commits
        async with self.get_client() as client:
            url = self.count_and_get_url_template(
                url_name="get_distance_in_commits"
            ).substitute(slug=self.slug, base_branch=base_branch, base=base)
            res = await self.api(client, "get", url, token=token)
        behind_by = res.get("behind_by")
        behind_by_commit = res["base_commit"]["sha"] if "base_commit" in res else None
        if behind_by is None or behind_by_commit is None:
            behind_by = None
            behind_by_commit = None
        return dict(
            behind_by=behind_by,
            behind_by_commit=behind_by_commit,
            status=res.get("status"),
            ahead_by=res.get("ahead_by"),
        )

    async def get_commit(self, commit, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        try:
            async with self.get_client() as client:
                res = await self.api(
                    client,
                    "get",
                    "/repos/%s/commits/%s" % (self.slug, commit),
                    statuses_to_retry=[401],
                    token=token,
                )
        except TorngitClientError as ce:
            if ce.code == 422:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"Commit with id {commit} does not exist",
                )
            if ce.code == 404:
                raise TorngitRepoNotFoundError(
                    response_data=ce.response_data,
                    message=f"Repo {self.slug} cannot be found by this user",
                )
            raise
        return dict(
            author=dict(
                id=str(res["author"]["id"]) if res["author"] else None,
                username=res["author"]["login"] if res["author"] else None,
                email=res["commit"]["author"].get("email"),
                name=res["commit"]["author"].get("name"),
            ),
            commitid=commit,
            parents=[p["sha"] for p in res["parents"]],
            message=res["commit"]["message"],
            timestamp=res["commit"]["committer"].get("date"),
        )

    # Pull Requests
    # -------------
    def _pull(self, pull):
        return dict(
            author=dict(
                id=str(pull["user"]["id"]) if pull["user"] else None,
                username=pull["user"]["login"] if pull["user"] else None,
            ),
            base=dict(
                branch=pull["base"]["ref"],
                commitid=pull["base"]["sha"],
                slug=pull["base"]["repo"]["full_name"],
            ),
            head=dict(
                branch=pull["head"]["ref"],
                commitid=pull["head"]["sha"],
                # Through empiric test data it seems that the "repo" key in "head" is set to None
                # If the PR is from the same repo (e.g. not from a fork)
                slug=(
                    pull["head"]["repo"]["full_name"]
                    if pull["head"]["repo"]
                    else pull["base"]["repo"]["full_name"]
                ),
            ),
            state="merged" if pull["merged"] else pull["state"],
            title=pull["title"],
            id=str(pull["number"]),
            number=str(pull["number"]),
            labels=[label["name"] for label in pull.get("labels", [])],
        )

    async def get_pull_request(self, pullid, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://developer.github.com/v3/pulls/#get-a-single-pull-request
        async with self.get_client() as client:
            try:
                url = self.count_and_get_url_template(
                    url_name="get_pull_request"
                ).substitute(slug=self.slug, pullid=pullid)
                res = await self.api(client, "get", url, token=token)
            except TorngitClientError as ce:
                if ce.code == 404:
                    raise TorngitObjectNotFoundError(
                        response_data=ce.response_data,
                        message=f"Pull Request {pullid} not found",
                    )
                raise
            commits = await self._get_raw_pull_request_commits(pullid, token)
            commit_mapping = {
                val["sha"]: [k["sha"] for k in val["parents"]] for val in commits
            }
            all_commits_in_pr = set([val["sha"] for val in commits])
            current_level = [res["head"]["sha"]]
            while current_level and all(x in all_commits_in_pr for x in current_level):
                new_level = []
                for x in current_level:
                    new_level.extend(commit_mapping[x])
                current_level = new_level
            result = self._pull(res)
            if current_level == [res["head"]["sha"]]:
                log.warning(
                    "Head not found in PR. PR has probably too many commits to list all of them",
                    extra=dict(number_commits=len(commits), pullid=pullid),
                )
            else:
                possible_bases = [
                    x for x in current_level if x not in all_commits_in_pr
                ]
                if possible_bases and result["base"]["commitid"] not in possible_bases:
                    log.info(
                        "Github base differs from original base",
                        extra=dict(
                            current_level=current_level,
                            github_base=result["base"]["commitid"],
                            possible_bases=possible_bases,
                            pullid=pullid,
                        ),
                    )
                    result["base"]["commitid"] = possible_bases[0]
            return result

    async def get_pull_requests(self, state="open", token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://developer.github.com/v3/pulls/#list-pull-requests
        page, pulls = 0, []
        async with self.get_client() as client:
            while True:
                page += 1
                url = self.count_and_get_url_template(
                    url_name="get_pull_requests"
                ).substitute(slug=self.slug)
                res = await self.api(
                    client,
                    "get",
                    url,
                    page=page,
                    per_page=25,
                    state=state,
                    token=token,
                )
                if len(res) == 0:
                    break

                pulls.extend([pull["number"] for pull in res])

                if len(pulls) < 25:
                    break

            return pulls

    async def find_pull_request(
        self, commit=None, branch=None, state="open", token=None
    ):
        if not self.slug or not commit:
            return None
        token = self.get_token_by_type_if_none(token, TokenType.read)
        async with self.get_client() as client:
            # https://docs.github.com/en/rest/commits/commits#list-pull-requests-associated-with-a-commit
            try:
                url = self.count_and_get_url_template(
                    url_name="find_pull_request"
                ).substitute(slug=self.slug, commit=commit)
                res = await self.api(client, "get", url, token=token)
                prs_with_commit = [
                    data["number"] for data in res if data["state"] == state
                ]
                if prs_with_commit:
                    if len(prs_with_commit) > 1:
                        log.warning(
                            "Commit is referenced in multiple PRs.",
                            extra=dict(
                                prs=prs_with_commit,
                                commit=commit,
                                slug=self.slug,
                                state=state,
                            ),
                        )
                    return prs_with_commit[0]
            except TorngitClientGeneralError as exp:
                if exp.code == 422:
                    return None
                raise exp

    async def get_pull_request_files(self, pullid, token=None):
        if not self.slug:
            return None
        token = self.get_token_by_type_if_none(token, TokenType.read)
        async with self.get_client() as client:
            # https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests-files
            try:
                url = self.count_and_get_url_template(
                    url_name="get_pull_request_files"
                ).substitute(slug=self.slug, pullid=pullid)
                res = await self.api(client, "get", url, token=token)
                filenames = [data.get("filename") for data in res]
                return filenames
            except TorngitClientError as ce:
                if ce.code == 404:
                    raise TorngitObjectNotFoundError(
                        response_data=ce.response_data,
                        message=f"PR with id {pullid} does not exist",
                    )
                raise

    async def list_top_level_files(self, ref, token=None):
        return await self.list_files(ref, dir_path="", token=None)

    async def list_files(self, ref, dir_path, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://developer.github.com/v3/repos/contents/#get-contents
        if dir_path:
            url = self.count_and_get_url_template(
                url_name="list_files_with_dir_path"
            ).substitute(slug=self.slug, dir_path=dir_path)
        else:
            url = self.count_and_get_url_template(url_name="list_files").substitute(
                slug=self.slug
            )
        async with self.get_client() as client:
            content = await self.api(client, "get", url, ref=ref, token=token)
        return [
            {
                "name": f["name"],
                "path": f["path"],
                "type": self._github_type_to_torngit_type(f["type"]),
            }
            for f in content
        ]

    def _github_type_to_torngit_type(self, val):
        if val == "file":
            return "file"
        elif val == "dir":
            return "folder"
        return "other"

    async def get_ancestors_tree(self, commitid, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        async with self.get_client() as client:
            url = self.count_and_get_url_template(
                url_name="get_ancestors_tree"
            ).substitute(slug=self.slug)
            res = await self.api(client, "get", url, token=token, sha=commitid)
        start = res[0]["sha"]
        commit_mapping = {val["sha"]: [k["sha"] for k in val["parents"]] for val in res}
        return self.build_tree_from_commits(start, commit_mapping)

    def get_external_endpoint(self, endpoint: Endpoints, **kwargs):
        # used in parent obj to get_href
        # I think this is for creating a clickable link,
        # not a token-using call by us, so not counting these calls.
        if endpoint == Endpoints.commit_detail:
            return external_endpoint_template.substitute(
                username=self.data["owner"]["username"],
                name=self.data["repo"]["name"],
                commitid=kwargs["commitid"],
            )
        raise NotImplementedError()

    # Checks Docs: https://developer.github.com/v3/checks/

    async def create_check_run(
        self, check_name, head_sha, status="in_progress", token=None
    ):
        async with self.get_client() as client:
            url = self.count_and_get_url_template(
                url_name="create_check_run"
            ).substitute(slug=self.slug)
            res = await self.api(
                client,
                "post",
                url,
                body=dict(name=check_name, head_sha=head_sha, status=status),
                token=token,
            )
            return res["id"]

    @torngit_cache.cache_function(
        torngit_cache.get_ttl("check"),
        log_hits=True,
        log_map={
            "args_indexes_to_log": [0, 1, 2],
            "kwargs_keys_to_log": ["check_suite_id", "head_sha", "name"],
        },
    )
    async def get_check_runs(
        self, check_suite_id=None, head_sha=None, name=None, token=None
    ):
        if check_suite_id is None and head_sha is None:
            raise Exception(
                "check_suite_id and head_sha parameter should not both be None"
            )
        url = ""
        if check_suite_id is not None:
            url = self.count_and_get_url_template(
                url_name="get_check_runs_with_check_suite_id"
            ).substitute(slug=self.slug, check_suite_id=check_suite_id)
        elif head_sha is not None:
            url = self.count_and_get_url_template(
                url_name="get_check_runs_with_head_sha"
            ).substitute(slug=self.slug, head_sha=head_sha)
        if name is not None:
            url += f"?check_name={name}"
        async with self.get_client() as client:
            res = await self.api(client, "get", url, token=token)
            return res

    async def get_check_suites(self, git_sha, token=None):
        async with self.get_client() as client:
            url = self.count_and_get_url_template(
                url_name="get_check_suites"
            ).substitute(slug=self.slug, git_sha=git_sha)
            res = await self.api(client, "get", url, token=token)
            return res

    # TODO: deprecated - favour the get_repos_with_languages_graphql() method instead
    async def get_repo_languages(self, token=None) -> List[str]:
        """
        Gets the languages belonging to this repository.
        Reference:
            https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-repository-languages
        Returns:
            List[str]: A list of language names
        """
        async with self.get_client() as client:
            url = self.count_and_get_url_template(
                url_name="get_repo_languages"
            ).substitute(slug=self.slug)
            res = await self.api(client, "get", url, token=token)
        return list(k.lower() for k in res.keys())

    async def get_repos_with_languages_graphql(
        self, owner_username: str, token=None, first=100
    ) -> dict[str, List[str]]:
        """
        Gets the languages belonging to repositories of a specific owner.
        Reference:
            https://docs.github.com/en/graphql/reference/objects#repository
        Returns:
            dict[str, str]: A dictionary with repo_name: [languages]
        """
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # Initially set to none and true
        endCursor = None
        hasNextPage = True
        all_repositories = {}

        async with self.get_client() as client:
            while hasNextPage:
                query = self.graphql.prepare(
                    "REPO_LANGUAGES_FROM_OWNER",
                    variables={
                        "owner": owner_username,
                        "cursor": endCursor,
                        "first": first,
                    },
                )
                url = self.count_and_get_url_template(
                    url_name="get_repos_with_languages_graphql"
                ).substitute()
                res = await self.api(client, "post", url, body=query, token=token)
                repoOwner = res["data"]["repositoryOwner"]
                if not repoOwner:
                    hasNextPage = False
                else:
                    repositories = repoOwner["repositories"]
                    hasNextPage = repositories["pageInfo"]["hasNextPage"]
                    endCursor = repositories["pageInfo"]["endCursor"]

                    for repo in repositories["nodes"]:
                        languages = repo["languages"]["edges"]
                        res_languages = []
                        for language in languages:
                            res_languages.append(language["node"]["name"].lower())

                        all_repositories[repo["name"]] = res_languages

        return all_repositories

    async def update_check_run(
        self,
        check_run_id,
        conclusion,
        status="completed",
        output=None,
        url=None,
        token=None,
    ):
        body = dict(conclusion=conclusion, status=status, output=output)
        if url:
            body["details_url"] = url
        async with self.get_client() as client:
            api_url = self.count_and_get_url_template(
                url_name="update_check_run"
            ).substitute(slug=self.slug, check_run_id=check_run_id)
            res = await self.api(client, "patch", api_url, body=body, token=token)
            return res

    # Get information for a GitHub Actions build/workflow run
    # -------------
    def actions_run_info(self, run):
        """
        This method formats the API response from GitHub Actions
        for any particular build/workflow run. All fields are relevant to
        validating a tokenless response.
        """
        public = True
        if run["repository"]["private"]:
            public = False
        return dict(
            start_time=run["created_at"],
            finish_time=run["updated_at"],
            status=run["status"],
            public=public,
            slug=run["repository"]["full_name"],
            commit_sha=run["head_sha"],
        )

    async def get_workflow_run(self, run_id, token=None):
        """
        GitHub defines a workflow and a run as the following properties:
        Workflow = yaml with build configuration options
        Run = one instance when the workflow was triggered
        """
        async with self.get_client() as client:
            url = self.count_and_get_url_template(
                url_name="get_workflow_run"
            ).substitute(slug=self.slug, run_id=run_id)
            res = await self.api(client, "get", url, token=token)
        return self.actions_run_info(res)

    def loggable_token(self, token) -> str:
        """Gets a "loggable" version of the current repo token.

        The idea here is to get something in the logs that is enough for us to make comparisons like
            "this log line is probably using the same token as this log line"

        But nothing else

        When there is a username, we will just log who owns that token

        For this, on the cases that there are no username, which is the case for integration tokens,
            we are taking the token, mixing it with a secret that is present only in the code,
            doing a sha256, base64-encoding and only logging the first 5 chars from it
            (from the original 44 chars)

        This, added with the fact that each token is valid only for 1 hour, should be enough
            for people not to be able to extract any useful information from it

        Returns:
            str: A good enough string to tell tokens apart
        """
        if token.get("username"):
            username = token.get("username")
            return f"{username}'s token"
        if token is None or token.get("key") is None:
            return "notoken"
        some_secret = "v1CAF4bFYi2+7sN7hgS/flGtooomdTZF0+uGiigV3AY8f4HHNg".encode()
        hasher = hashlib.sha256()
        hasher.update(some_secret)
        hasher.update(self.service.encode())
        if self.slug:
            hasher.update(self.slug.encode())
        hasher.update(token.get("key").encode())
        return base64.b64encode(hasher.digest()).decode()[:5]

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
        url = self.count_and_get_url_template(
            url_name="get_best_effort_branches"
        ).substitute(slug=self.slug, commit_sha=commit_sha)
        async with self.get_client() as client:
            res = await self.api(
                client,
                "get",
                url,
                token=token,
                headers={"Accept": "application/vnd.github.groot-preview+json"},
            )
            return [r["name"] for r in res]

    async def is_student(self):
        async with self.get_client([3, 3]) as client:
            try:
                url = self.count_and_get_url_template(
                    url_name="is_student"
                ).substitute()
                res = await self.api(client, "get", url)
                return res["student"]
            except TorngitServerUnreachableError:
                log.warning("Timeout on Github Education API for is_student")
                return False
            except (TorngitUnauthorizedError, TorngitServer5xxCodeError):
                return False

    # GitHub App Webhook management
    # =============================
    async def list_webhook_deliveries(self):
        """
        Lists the webhook deliveries for the gh app.
        docs: https://docs.github.com/en/rest/apps/webhooks?apiVersion=2022-11-28#list-deliveries-for-an-app-webhook

        This is a generator function that yields the pages from webhook deliveries until all have been requested.
        Page size is 50.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token['key']}",
        }
        async with self.get_client() as client:
            # self.count_and_get_url_template is called in paginated_api_generator
            async for response in self.paginated_api_generator(
                client,
                "get",
                url_name="list_webhook_deliveries",
                headers=headers,
            ):
                yield response

    async def request_webhook_redelivery(self, delivery_id: str) -> bool:
        """
        Request redelivery of a webhook from github app. Returns True if request is successful, False otherwise.
        docs: https://docs.github.com/en/rest/apps/webhooks?apiVersion=2022-11-28#redeliver-a-delivery-for-an-app-webhook
        """
        url = self.count_and_get_url_template(
            url_name="request_webhook_redelivery"
        ).substitute(delivery_id=delivery_id)
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token['key']}",
        }
        async with self.get_client() as client:
            try:
                await self.api(client, "post", url, headers=headers)
                return True
            except (TorngitClientError, TorngitServer5xxCodeError):
                return False
