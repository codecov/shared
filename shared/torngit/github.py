import base64
import hashlib
import logging
import os
from base64 import b64decode
from typing import List

import httpx
from httpx import Response

from shared.metrics import metrics
from shared.torngit.base import TokenType, TorngitBaseAdapter
from shared.torngit.cache import torngit_cache
from shared.torngit.enums import Endpoints
from shared.torngit.exceptions import (
    TorngitClientError,
    TorngitClientGeneralError,
    TorngitMisconfiguredCredentials,
    TorngitObjectNotFoundError,
    TorngitRateLimitError,
    TorngitRepoNotFoundError,
    TorngitServer5xxCodeError,
    TorngitServerUnreachableError,
    TorngitUnauthorizedError,
)
from shared.torngit.status import Status
from shared.utils.urls import url_concat

log = logging.getLogger(__name__)

METRICS_PREFIX = "services.torngit.github"


class Github(TorngitBaseAdapter):
    service = "github"
    service_url = "https://github.com"
    api_url = "https://api.github.com"
    urls = dict(
        repo="{username}/{name}",
        owner="{username}",
        user="{username}",
        issues="{username}/{name}/issues/%(issueid)s",
        commit="{username}/{name}/commit/{commitid}",
        commits="{username}/{name}/commits",
        compare="{username}/{name}/compare/%(base)s...%(head)s",
        comment="{username}/{name}/issues/%(pullid)s#issuecomment-%(commentid)s",
        create_file="{username}/{name}/new/%(branch)s?filename=%(path)s&value=%(content)s",
        pull="{username}/{name}/pull/%(pullid)s",
        branch="{username}/{name}/tree/%(branch)s",
        tree="{username}/{name}/tree/%(commitid)s",
        src="{username}/{name}/blob/%(commitid)s/%(path)s",
        author="{username}/{name}/commits?author=%(author)s",
    )

    @property
    def token(self):
        return self._token

    async def api(self, *args, token=None, **kwargs):
        """
        Makes a single http request to GitHub and returns the parsed response
        """
        token_to_use = token or self.token
        if not token_to_use:
            raise TorngitMisconfiguredCredentials()
        response = await self.make_http_call(*args, token_to_use=token_to_use, **kwargs)
        return self._parse_response(response)

    async def paginated_api_generator(
        self, client, method, initial_url, token=None, **kwargs
    ):
        """
        Generator that requests pages from GitHub and yields each page as they come.
        Continues to request pages while there's a link to the next page.
        """
        token_to_use = token or self.token
        if not token_to_use:
            raise TorngitMisconfiguredCredentials()
        url = initial_url
        while url:
            args = [client, method, url]
            response = await self.make_http_call(
                *args, token_to_use=token_to_use, **kwargs
            )
            yield self._parse_response(response)
            url = response.links.get("next", {}).get("url", "")

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

        kwargs = dict(
            json=body if body else None, headers=_headers, follow_redirects=False
        )
        max_number_retries = 3
        for current_retry in range(1, max_number_retries + 1):
            try:
                with metrics.timer(f"{METRICS_PREFIX}.api.run") as timer:
                    res = await client.request(method, url, **kwargs)
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
                        rlx=res.headers.get("X-RateLimit-Remaining"),
                        rly=res.headers.get("X-RateLimit-Limit"),
                        rlr=res.headers.get("X-RateLimit-Reset"),
                        retry_after=res.headers.get("Retry-After"),
                        **log_dict,
                    ),
                )
            except (httpx.TimeoutException, httpx.NetworkError):
                metrics.incr(f"{METRICS_PREFIX}.api.unreachable")
                raise TorngitServerUnreachableError(
                    "GitHub was not able to be reached."
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
                elif (
                    res.status_code == 403
                    and int(res.headers.get("X-RateLimit-Remaining", -1)) == 0
                ):
                    message = f"Github API rate limit error: {res.reason_phrase}"
                    metrics.incr(f"{METRICS_PREFIX}.api.ratelimiterror")
                    raise TorngitRateLimitError(
                        response_data=res.text,
                        message=message,
                        reset=res.headers.get("X-RateLimit-Reset"),
                    )
                elif (
                    res.status_code == 403
                    and res.headers.get("Retry-After") is not None
                ):
                    # https://docs.github.com/en/rest/overview/resources-in-the-rest-api?apiVersion=2022-11-28#secondary-rate-limits
                    message = f"Github API rate limit error: secondary rate limit"
                    retry_after = int(res.headers.get("Retry-After"))
                    metrics.incr(f"{METRICS_PREFIX}.api.ratelimiterror")
                    raise TorngitRateLimitError(
                        response_data=res.text,
                        message=message,
                        retry_after=retry_after,
                    )
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
                    "Retrying due to retriable status",
                    extra=dict(status=res.status_code, **log_dict),
                )

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
                res = await self.api(
                    client,
                    "get",
                    "/repos/%s/branches" % self.slug,
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

    async def get_authenticated_user(self, code):
        creds = self._oauth_consumer_token()
        async with self.get_client() as client:
            response = await self.make_http_call(
                client,
                "get",
                self.service_url + "/login/oauth/access_token",
                code=code,
                client_id=creds["key"],
                client_secret=creds["secret"],
            )
            session = self._parse_response(response)

            if session.get("access_token"):
                # set current token
                self.set_token(dict(key=session["access_token"]))

                user = await self.api(client, "get", "/user")
                user.update(session or {})
                email = user.get("email")
                if not email:
                    emails = await self.api(client, "get", "/user/emails")
                    emails = [e["email"] for e in emails if e["primary"]]
                    user["email"] = emails[0] if emails else None
                return user

            else:
                return None

    async def get_is_admin(self, user, token=None):
        async with self.get_client() as client:
            # https://developer.github.com/v3/orgs/members/#get-organization-membership
            res = await self.api(
                client,
                "get",
                "/orgs/%s/memberships/%s"
                % (self.data["owner"]["username"], user["username"]),
                token=token,
            )
            return res["state"] == "active" and res["role"] == "admin"

    async def get_authenticated(self, token=None):
        """Returns (can_view, can_edit)"""
        # https://developer.github.com/v3/repos/#get
        async with self.get_client() as client:
            r = await self.api(client, "get", "/repos/%s" % self.slug, token=token)
            ok = r["permissions"]["admin"] or r["permissions"]["push"]
            return (True, ok)

    async def get_repository(self, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        async with self.get_client() as client:
            if self.data["repo"].get("service_id") is None:
                # https://developer.github.com/v3/repos/#get
                res = await self.api(
                    client, "get", "/repos/%s" % self.slug, token=token
                )
            else:
                res = await self.api(
                    client,
                    "get",
                    "/repositories/%s" % self.data["repo"]["service_id"],
                    token=token,
                )

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

    async def list_repos_using_installation(self, username=None):
        """
        returns list of repositories included in this integration
        """
        page = 0
        async with self.get_client() as client:
            while True:
                repos = []
                page += 1
                # https://docs.github.com/en/rest/apps/installations?apiVersion=2022-11-28
                res = await self.api(
                    client,
                    "get",
                    "/installation/repositories?per_page=100&page=%d" % page,
                    headers={
                        "Accept": "application/vnd.github.machine-man-preview+json",
                    },
                )
                if len(res["repositories"]) == 0:
                    break

                for repo in res["repositories"]:
                    repos.append(
                        dict(
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
                    )

                yield repos

                if len(repos) < 100:
                    break

    async def list_repos(self, username=None, token=None):
        """
        GitHub includes all visible repos through
        the same endpoint.
        """
        token = self.get_token_by_type_if_none(token, TokenType.read)
        page = 0
        async with self.get_client() as client:
            while True:
                data = []
                page += 1
                # https://developer.github.com/v3/repos/#list-your-repositories
                if username is None:
                    repos = await self.api(
                        client,
                        "get",
                        "/user/repos?per_page=100&page=%d" % page,
                        token=token,
                    )
                else:
                    repos = await self.api(
                        client,
                        "get",
                        "/users/%s/repos?per_page=100&page=%d" % (username, page),
                        token=token,
                    )

                for repo in repos:
                    _o, _r = repo["owner"]["login"], repo["name"]

                    data.append(
                        dict(
                            owner=dict(
                                service_id=str(repo["owner"]["id"]), username=_o
                            ),
                            repo=dict(
                                service_id=str(repo["id"]),
                                name=_r,
                                language=self._validate_language(repo["language"]),
                                private=repo["private"],
                                branch=repo["default_branch"],
                            ),
                        )
                    )

                yield data

                if len(repos) < 100:
                    break

    async def list_teams(self, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.admin)
        # https://developer.github.com/v3/orgs/#list-your-organizations
        page, data = 0, []
        async with self.get_client() as client:
            while True:
                page += 1
                orgs = await self.api(
                    client,
                    "get",
                    "/user/memberships/orgs?state=active",
                    page=page,
                    token=token,
                )
                if len(orgs) == 0:
                    break
                # organization names
                for org in orgs:
                    try:
                        organization = org["organization"]
                        org = await self.api(
                            client,
                            "get",
                            "/users/%s" % organization["login"],
                            token=token,
                        )
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
        # https://developer.github.com/v3/pulls/#list-commits-on-a-pull-request
        # NOTE limited to 250 commits
        async with self.get_client() as client:
            res = await self.api(
                client,
                "get",
                "/repos/%s/pulls/%s/commits" % (self.slug, pullid),
                token=token,
            )
            return [c["sha"] for c in res]

    # Webhook
    # -------
    async def post_webhook(self, name, url, events, secret, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.admin)
        # https://developer.github.com/v3/repos/hooks/#create-a-hook
        async with self.get_client() as client:
            res = await self.api(
                client,
                "post",
                "/repos/%s/hooks" % self.slug,
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
                return await self.api(
                    client,
                    "patch",
                    "/repos/%s/hooks/%s" % (self.slug, hookid),
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
                await self.api(
                    client,
                    "delete",
                    "/repos/%s/hooks/%s" % (self.slug, hookid),
                    token=token,
                )
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
            res = await self.api(
                client,
                "post",
                "/repos/%s/issues/%s/comments" % (self.slug, issueid),
                body=dict(body=body),
                token=token,
            )
            return res

    async def edit_comment(self, issueid, commentid, body, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.comment)
        # https://developer.github.com/v3/issues/comments/#edit-a-comment
        try:
            async with self.get_client() as client:
                return await self.api(
                    client,
                    "patch",
                    "/repos/%s/issues/comments/%s" % (self.slug, commentid),
                    body=dict(body=body),
                    token=token,
                )
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
                await self.api(
                    client,
                    "delete",
                    "/repos/%s/issues/comments/%s" % (self.slug, commentid),
                    token=token,
                )
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
                res = await self.api(
                    client,
                    "post",
                    "/repos/%s/statuses/%s" % (self.slug, commit),
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
                await self.api(
                    client,
                    "post",
                    "/repos/%s/statuses/%s" % (self.slug, merge_commit[0]),
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
                res = await self.api(
                    client,
                    "get",
                    "/repos/%s/commits/%s/status" % (self.slug, commit),
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
                content = await self.api(
                    client,
                    "get",
                    "/repos/{0}/contents/{1}".format(
                        self.slug, path.replace(" ", "%20")
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
        return dict(content=b64decode(content["content"]), commitid=content["sha"])

    async def get_commit_diff(self, commit, context=None, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        try:
            async with self.get_client() as client:
                res = await self.api(
                    client,
                    "get",
                    "/repos/%s/commits/%s" % (self.slug, commit),
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
            res = await self.api(
                client,
                "get",
                "/repos/%s/compare/%s...%s" % (self.slug, base, head),
                token=token,
            )
        files = {}
        for f in res["files"]:
            diff = self.diff_to_json(
                "diff --git a/%s b/%s%s\n%s\n%s\n%s"
                % (
                    f.get("previous_filename") or f.get("filename"),
                    f.get("filename"),
                    "\ndeleted file mode 100644"
                    if f["status"] == "removed"
                    else "\nnew file mode 100644"
                    if f["status"] == "added"
                    else "",
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
            res = await self.api(
                client,
                "get",
                "/repos/%s/compare/%s...%s" % (self.slug, base_branch, base),
                token=token,
            )
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
            timestamp=res["commit"]["author"].get("date"),
        )

    # Pull Requests
    # -------------
    def _pull(self, pull):
        return dict(
            author=dict(
                id=str(pull["user"]["id"]) if pull["user"] else None,
                username=pull["user"]["login"] if pull["user"] else None,
            ),
            base=dict(branch=pull["base"]["ref"], commitid=pull["base"]["sha"]),
            head=dict(branch=pull["head"]["ref"], commitid=pull["head"]["sha"]),
            state="merged" if pull["merged"] else pull["state"],
            title=pull["title"],
            id=str(pull["number"]),
            number=str(pull["number"]),
        )

    async def get_pull_request(self, pullid, token=None):
        token = self.get_token_by_type_if_none(token, TokenType.read)
        # https://developer.github.com/v3/pulls/#get-a-single-pull-request
        async with self.get_client() as client:
            try:
                res = await self.api(
                    client,
                    "get",
                    "/repos/%s/pulls/%s" % (self.slug, pullid),
                    token=token,
                )
            except TorngitClientError as ce:
                if ce.code == 404:
                    raise TorngitObjectNotFoundError(
                        response_data=ce.response_data,
                        message=f"Pull Request {pullid} not found",
                    )
                raise
            commits = await self.api(
                client,
                "get",
                "/repos/%s/pulls/%s/commits" % (self.slug, pullid),
                token=token,
                per_page=250,
            )
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
                res = await self.api(
                    client,
                    "get",
                    "/repos/%s/pulls" % self.slug,
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
                res = await self.api(
                    client,
                    "get",
                    f"/repos/{self.slug}/commits/{commit}/pulls",
                    token=token,
                )
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
                res = await self.api(
                    client,
                    "get",
                    f"/repos/{self.slug}/pulls/{pullid}/files",
                    token=token,
                )
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
            url = f"/repos/{self.slug}/contents/{dir_path}"
        else:
            url = f"/repos/{self.slug}/contents"
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
            res = await self.api(
                client,
                "get",
                "/repos/%s/commits" % self.slug,
                token=token,
                sha=commitid,
            )
        start = res[0]["sha"]
        commit_mapping = {val["sha"]: [k["sha"] for k in val["parents"]] for val in res}
        return self.build_tree_from_commits(start, commit_mapping)

    def get_external_endpoint(self, endpoint: Endpoints, **kwargs):
        if endpoint == Endpoints.commit_detail:
            return self.urls["commit"].format(
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
            res = await self.api(
                client,
                "post",
                "/repos/{}/check-runs".format(self.slug),
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
            url = (
                "/repos/{}/check-suites/{}/check-runs".format(
                    self.slug, check_suite_id
                ),
            )
        elif head_sha is not None:
            url = "/repos/{}/commits/{}/check-runs".format(self.slug, head_sha)
        if name is not None:
            url += "?check_name={}".format(name)
        async with self.get_client() as client:
            res = await self.api(client, "get", url, token=token)
            return res

    async def get_check_suites(self, git_sha, token=None):
        async with self.get_client() as client:
            res = await self.api(
                client,
                "get",
                "/repos/{}/commits/{}/check-suites".format(self.slug, git_sha),
                token=token,
            )
            return res

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
            res = await self.api(
                client,
                "patch",
                "/repos/{}/check-runs/{}".format(self.slug, check_run_id),
                body=body,
                token=token,
            )
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
            res = await self.api(
                client,
                "get",
                "/repos/%s/actions/runs/%s" % (self.slug, run_id),
                token=token,
            )
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
        url = f"/repos/{self.slug}/commits/{commit_sha}/branches-where-head"
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
        async with self.get_client() as client:
            try:
                res = await self.api(
                    client, "get", "https://education.github.com/api/user"
                )
                return res["student"]
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
        base_url = "/app/hook/deliveries"
        url = base_url + "?per_page=50"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token['key']}",
        }
        async with self.get_client() as client:
            async for response in self.paginated_api_generator(
                client,
                "get",
                url,
                headers=headers,
            ):
                yield response

    async def request_webhook_redelivery(self, delivery_id: str) -> bool:
        """
        Request redelivery of a webhook from github app. Returns True if request is successful, False otherwise.
        docs: https://docs.github.com/en/rest/apps/webhooks?apiVersion=2022-11-28#redeliver-a-delivery-for-an-app-webhook
        """
        url = f"/app/hook/deliveries/{delivery_id}/attempts"
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
