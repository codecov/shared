import json
import logging
import os
from base64 import b64decode
from typing import List
from urllib.parse import quote, urlencode

import httpx

from shared.config import get_config
from shared.metrics import metrics
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


class Gitlab(TorngitBaseAdapter):
    service = "gitlab"
    service_url = "https://gitlab.com"
    api_url = "https://gitlab.com/api/v{}"
    urls = dict(
        owner="{username}",
        user="{username}",
        repo="{username}/{name}",
        issues="{username}/{name}/issues/%(issueid)s",
        commit="{username}/{name}/commit/{commitid}",
        commits="{username}/{name}/commits",
        compare="{username}/{name}/compare/%(base)s...%(head)s",
        create_file="{username}/{name}/new/%(branch)s?file_name=%(path)s&content=%(content)s",
        src="{username}/{name}/blob/%(commitid)s/%(path)s",
        branch="{username}/{name}/tree/%(branch)s",
        pull="{username}/{name}/merge_requests/%(pullid)s",
        tree="{username}/{name}/tree/%(commitid)s",
    )

    @property
    def redirect_uri(self):
        from_config = get_config("gitlab", "redirect_uri", default=None)
        if from_config is not None:
            return from_config
        base = get_config("setup", "codecov_url", default="https://codecov.io")
        return base + "/login/gitlab"

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

        current_retry = 0
        max_retries = 2
        while current_retry < max_retries:
            current_retry += 1

            if token or self.token:
                headers["Authorization"] = "Bearer %s" % (token or self.token)["key"]

            try:
                with metrics.timer(f"{METRICS_PREFIX}.api.run") as timer:
                    res = await client.request(
                        method.upper(), url, headers=headers, data=body
                    )
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
        res = await client.request(
            "POST", self.service_url + "/oauth/token", data=params, params=params
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
                yield None if current_result.status_code == 204 else current_result.json()
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
        Get's access_token and user's details from gitlab.

        Exchanges the code for a proper access_token and refresh_token pair.
        Get's user details from /user endpoint from GitLab.
        Returns everything.

        Args:
            code: the code to be redeemed for a access_token / refresh_token pair
            redirect_uri: !deprecated. The uri to redirect to. Needs to match redirect_uri used to get the code.
        """
        creds_from_token = self._oauth_consumer_token()
        creds_to_send = dict(
            client_id=creds_from_token["key"], client_secret=creds_from_token["secret"]
        )
        redirect_uri = redirect_uri or self.redirect_uri

        # http://doc.gitlab.com/ce/api/oauth2.html
        res = await self.api(
            "post",
            self.service_url + "/oauth/token",
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
        res = await self.api(
            "post",
            "/projects/%s/hooks" % self.data["repo"]["service_id"],
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
        return await self.api(
            "put",
            "/projects/%s/hooks/%s" % (self.data["repo"]["service_id"], hookid),
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
        try:
            await self.api(
                "delete",
                "/projects/%s/hooks/%s" % (self.data["repo"]["service_id"], hookid),
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
            user_info = await self.api(
                "get", "/users?username={}".format(username), token=token
            )
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
        user = await self.api("get", "/user", token=token)
        user["is_user"] = True
        if username:
            if username.lower() == user["username"].lower():
                # just me
                groups = [user]
            else:
                # a group
                groups = [
                    (await self.api("get", "/groups/{}".format(username), token=token))
                ]
        else:
            # user and all groups
            groups = await self.api("get", "/groups?per_page=100", token=token)
            groups.append(user)

        data = []
        for group in groups:
            page = 0
            while True:
                page += 1
                # http://doc.gitlab.com/ce/api/projects.html#projects
                if group.get("is_user"):
                    repos = await self.api(
                        "get",
                        "/projects?owned=true&per_page=50&page={}".format(page),
                        token=token,
                    )
                else:
                    try:
                        repos = await self.api(
                            "get",
                            "/groups/{}/projects?per_page=50&page={}".format(
                                group["id"], page
                            ),
                            token=token,
                        )
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
        async_generator = self.make_paginated_call(
            "/groups", max_per_page=100, default_kwargs={}, token=token
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
        try:
            pull = await self.api(
                "get",
                "/projects/{}/merge_requests/{}".format(
                    self.data["repo"]["service_id"], pullid
                ),
                token=token,
            )
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    response_data=ce.response_data,
                    message=f"PR with id {pullid} does not exist",
                )
            raise

        if pull:
            parent = None
            if pull.get("diff_refs", {}) and pull.get("diff_refs", {}).get("base_sha"):
                parent = pull.get("diff_refs", {}).get("base_sha")
            else:
                log.info(
                    "Could not fetch pull base from diff_refs",
                    extra=dict(pullid=pullid, pull_information=pull),
                )
                # get list of commits and first one out
                all_commits = await self.api(
                    "get",
                    "/projects/{}/merge_requests/{}/commits".format(
                        self.data["repo"]["service_id"], pullid
                    ),
                    token=token,
                )
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
                    parent = (
                        await self.api(
                            "get",
                            "/projects/{}/repository/commits/{}".format(
                                self.data["repo"]["service_id"], first_commit["id"]
                            ),
                            token=token,
                        )
                    )["parent_ids"][0]

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
        try:
            diffs = await self.api(
                "get",
                "/projects/{}/merge_requests/{}/diffs".format(
                    self.data["repo"]["service_id"], pullid
                ),
                token=token,
            )
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
        try:
            res = await self.api(
                "post",
                "/projects/%s/statuses/%s" % (self.data["repo"]["service_id"], commit),
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
            await self.api(
                "post",
                "/projects/%s/statuses/%s"
                % (self.data["repo"]["service_id"], merge_commit[0]),
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
        statuses_response = await self.api(
            "get",
            "/projects/%s/repository/commits/%s/statuses"
            % (self.data["repo"]["service_id"], commit),
            token=token,
        )

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
        return await self.api(
            "post",
            "/projects/%s/merge_requests/%s/notes"
            % (self.data["repo"]["service_id"], pullid),
            body=dict(body=body),
            token=token,
        )

    async def edit_comment(self, pullid, commentid, body, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.comment)
        # http://doc.gitlab.com/ce/api/notes.html#modify-existing-merge-request-note
        try:
            return await self.api(
                "put",
                "/projects/%s/merge_requests/%s/notes/%s"
                % (self.data["repo"]["service_id"], pullid, commentid),
                body=dict(body=body),
                token=token,
            )
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
        try:
            await self.api(
                "delete",
                "/projects/%s/merge_requests/%s/notes/%s"
                % (self.data["repo"]["service_id"], pullid, commentid),
                token=token,
            )
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
        try:
            res = await self.api(
                "get",
                "/projects/%s/repository/commits/%s"
                % (self.data["repo"]["service_id"], commit),
                token=token,
            )
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
        authors = await self.api("get", "/users", search=email or name, token=token)
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
        commits = await self.api(
            "get",
            "/projects/{}/merge_requests/{}/commits".format(
                self.data["repo"]["service_id"], pullid
            ),
            token=token,
        )
        return [c["id"] for c in commits]

    async def get_branches(self, token=None):
        # http://doc.gitlab.com/ce/api/projects.html#list-branches
        token = self.get_token_by_type_if_none(token, TokenType.read)
        res = await self.api(
            "get",
            "/projects/%s/repository/branches" % self.data["repo"]["service_id"],
            token=token,
        )
        return [(b["name"], b["commit"]["id"]) for b in res]

    async def get_branch(self, name, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://docs.gitlab.com/ee/api/branches.html
        branch = await self.api(
            "get",
            "/projects/%s/repository/branches/%s"
            % (self.data["repo"]["service_id"], name),
            token=token,
        )
        return {"name": branch["name"], "sha": branch["commit"]["id"]}

    async def get_pull_requests(self, state="open", token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # ONLY searchable by branch.
        state = {"merged": "merged", "open": "opened", "close": "closed"}.get(
            state, "all"
        )
        # [TODO] pagination coming soon
        # http://doc.gitlab.com/ce/api/merge_requests.html#list-merge-requests
        res = await self.api(
            "get",
            "/projects/%s/merge_requests?state=%s"
            % (self.data["repo"]["service_id"], state),
            token=token,
        )
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
            try:
                res = await self.api(
                    "get",
                    "/projects/{}/repository/commits/{}/merge_requests".format(
                        self.data["repo"]["service_id"], commit
                    ),
                    token=token,
                )
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
            res = await self.api(
                "get",
                "/projects/%s/merge_requests?state=%s"
                % (self.data["repo"]["service_id"], gitlab_state),
                token=token,
            )
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
        try:
            res = await self.api(
                "get", "/projects/%s" % self.data["repo"]["service_id"], token=token
            )
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
        res = await self.api(
            "get",
            "/groups/{}/members/all/{}".format(
                self.data["owner"]["service_id"], user_id
            ),
            token=token,
        )
        return bool(res["state"] == "active" and res["access_level"] > 39)

    async def get_commit_diff(self, commit, context=None, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # http://doc.gitlab.com/ce/api/commits.html#get-the-diff-of-a-commit
        res = await self.api(
            "get",
            "/projects/%s/repository/commits/%s/diff"
            % (self.data["repo"]["service_id"], commit),
            token=token,
        )
        return self.diff_to_json(res)

    async def get_repository(self, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://docs.gitlab.com/ce/api/projects.html#get-single-project
        if self.data["repo"].get("service_id") is None:
            # convert from codecov ':' separator to gitlab '/' separator for groups/subgroups
            slug = self.slug.replace(":", "/")
            res = await self.api(
                "get", "/projects/" + slug.replace("/", "%2F"), token=token
            )
        else:
            res = await self.api(
                "get", "/projects/" + self.data["repo"]["service_id"], token=token
            )

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
        res = await self.api(
            "get",
            "/projects/%s/languages" % (self.data["repo"]["service_id"]),
            token=token,
        )
        return list(k.lower() for k in res.keys())

    async def get_source(self, path, ref, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://docs.gitlab.com/ce/api/repository_files.html#get-file-from-repository
        try:
            res = await self.api(
                "get",
                "/projects/{}/repository/files/{}".format(
                    self.data["repo"]["service_id"],
                    urlencode(dict(a=path), quote_via=quote)[2:],
                ),
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
        compare = await self.api(
            "get",
            "/projects/{}/repository/compare/?from={}&to={}".format(
                self.data["repo"]["service_id"], base, head
            ),
            token=token,
        )

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
        async_generator = self.make_paginated_call(
            f"/projects/{self.data['repo']['service_id']}/repository/tree",
            default_kwargs=dict(ref=ref, path=dir_path),
            max_per_page=100,
            token=token,
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
        res = await self.api(
            "get",
            "/projects/%s/repository/commits" % self.data["repo"]["service_id"],
            token=token,
            ref_name=commitid,
        )
        start = res[0]["id"]
        commit_mapping = {val["id"]: val["parent_ids"] for val in res}
        return self.build_tree_from_commits(start, commit_mapping)

    def get_external_endpoint(self, endpoint: Endpoints, **kwargs):
        if endpoint == Endpoints.commit_detail:
            return self.urls["commit"].format(
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
        async_generator = self.make_paginated_call(
            f"/projects/{self.data['repo']['service_id']}/repository/commits/{commit_sha}/refs?type=branch",
            default_kwargs=dict(),
            max_per_page=100,
            token=token,
        )
        all_results = []
        async for page in async_generator:
            for res in page:
                all_results.append(res["name"])
        return all_results

    async def is_student(self):
        return False
