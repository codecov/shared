from json import dumps
from json import loads
from time import time
import os
import urllib.parse as urllib_parse
import logging

from tornado.auth import OAuthMixin
from tornado.httpclient import HTTPError as ClientError
from tornado.httputil import url_concat

from shared.metrics import metrics
from shared.torngit.base import BaseHandler
from shared.torngit.enums import Endpoints
from shared.torngit.status import Status
from shared.torngit.exceptions import (
    TorngitObjectNotFoundError,
    TorngitServerUnreachableError,
    TorngitServer5xxCodeError,
    TorngitClientError,
)

log = logging.getLogger(__name__)

METRICS_PREFIX = "services.torngit.bitbucket"


class Bitbucket(BaseHandler, OAuthMixin):
    _OAUTH_REQUEST_TOKEN_URL = "https://bitbucket.org/api/1.0/oauth/request_token"
    _OAUTH_ACCESS_TOKEN_URL = "https://bitbucket.org/api/1.0/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "https://bitbucket.org/api/1.0/oauth/authenticate"
    _OAUTH_VERSION = "1.0a"
    service = "bitbucket"
    api_url = "https://bitbucket.org"
    service_url = "https://bitbucket.org"
    urls = dict(
        repo="{username}/{name}",
        owner="{username}",
        user="{username}",
        issues="{username}/{name}/issues/{issueid}",
        commit="{username}/{name}/commits/{commitid}",
        commits="{username}/{name}/commits",
        src="{username}/{name}/src/{commitid}/{path}",
        create_file="{username}/{name}/create-file/{commitid}?at={branch}&filename={path}&content={content}",
        tree="{username}/{name}/src/{commitid}",
        branch="{username}/{name}/branch/{branch}",
        pull="{username}/{name}/pull-requests/{pullid}",
        compare="{username}/{name}",
    )

    async def api(
        self, version, method, path, json=False, body=None, token=None, **kwargs
    ):
        url = "https://bitbucket.org/api/%s.0%s" % (version, path)
        headers = {
            "Accept": "application/json",
            "User-Agent": os.getenv("USER_AGENT", "Default"),
        }

        # make oauth request
        all_args = {}
        all_args.update(kwargs)
        if json:
            headers["Content-Type"] = "application/json"
        else:
            all_args.update(body or {})
        oauth = self._oauth_request_parameters(
            url, token or self.token, all_args, method=method.upper()
        )
        kwargs.update(oauth)

        url = url_concat(url, kwargs)
        kwargs = dict(
            method=method.upper(),
            body=dumps(body)
            if json
            else urllib_parse.urlencode(body)
            if body
            else None,
            ca_certs=self.verify_ssl if not isinstance(self.verify_ssl, bool) else None,
            validate_cert=self.verify_ssl
            if isinstance(self.verify_ssl, bool)
            else None,
            headers=headers,
            connect_timeout=self._timeouts[0],
            request_timeout=self._timeouts[1],
        )

        try:
            with metrics.timer(f"{METRICS_PREFIX}.api.run"):
                res = await self.fetch(url, **kwargs)
        except ClientError as e:
            if e.code == 599:
                metrics.incr(f"{METRICS_PREFIX}.api.unreachable")
                raise TorngitServerUnreachableError(
                    "Bitbucket was not able to be reached, server timed out."
                )
            elif e.code >= 500:
                metrics.incr(f"{METRICS_PREFIX}.api.5xx")
                raise TorngitServer5xxCodeError("Bitbucket is having 5xx issues")
            log.warning(
                "Bitbucket HTTP %s" % e.response.code,
                extra=dict(url=url, endpoint=path, body=e.response.body),
            )
            message = f"Bitbucket API: {e.message}"
            metrics.incr(f"{METRICS_PREFIX}.api.clienterror")
            raise TorngitClientError(e.code, e.response, message)
        else:
            log.info("Bitbucket HTTP %s" % res.code, extra=dict(url=url, endpoint=path))
            if res.code == 204:
                return None

            elif "application/json" in res.headers.get("Content-Type"):
                return loads(res.body)

            else:
                return res.body

    async def _oauth_get_user_future(self, access_token):
        self.set_token(access_token)
        user = await self.api("2", "get", "/user")
        return user

    async def post_webhook(self, name, url, events, secret, token=None):
        # https://confluence.atlassian.com/bitbucket/webhooks-resource-735642279.html
        # https://confluence.atlassian.com/bitbucket/event-payloads-740262817.html
        res = await self.api(
            "2",
            "post",
            "/repositories/%s/hooks" % self.slug,
            body=dict(description=name, active=True, events=events, url=url),
            json=True,
            token=token,
        )
        res["id"] = res["uuid"][1:-1]
        return res

    async def edit_webhook(self, hookid, name, url, events, secret, token=None):
        # https://confluence.atlassian.com/bitbucket/webhooks-resource-735642279.html#webhooksResource-PUTawebhookupdate
        res = await self.api(
            "2",
            "put",
            "/repositories/%s/hooks/%s" % (self.slug, hookid),
            body=dict(description=name, active=True, events=events, url=url),
            json=True,
            token=token,
        )
        res["id"] = res["uuid"][1:-1]
        return res

    async def delete_webhook(self, hookid, token=None):
        # https://confluence.atlassian.com/bitbucket/webhooks-resource-735642279.html#webhooksResource-DELETEthewebhook
        try:
            await self.api(
                "2",
                "delete",
                "/repositories/%s/hooks/%s" % (self.slug, hookid),
                token=token,
            )
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    ce.response, f"Webhook with id {hookid} does not exist"
                )
            raise
        return True

    async def get_is_admin(self, user, token=None):
        # https://confluence.atlassian.com/bitbucket/user-endpoint-296092264.html#userEndpoint-GETalistofuserprivileges
        groups = await self.api(
            "2",
            "get",
            "/user/permissions/teams",
            token=token,
            q='team.uuid="{' + self.data["owner"]["service_id"] + '}"',
        )
        if groups["values"]:
            for group in groups["values"]:
                if (
                    self.data["owner"]["username"] == group["team"]["username"]
                    and group["permission"] == "admin"
                ):
                    return True

        return False

    async def list_teams(self, token=None):
        teams, page = [], None
        while True:
            if page is not None:
                kwargs = dict(page=page, token=token)
            else:
                kwargs = dict(token=token)
            # https://confluence.atlassian.com/bitbucket/pullrequests-resource-423626332.html#pullrequestsResource-GETthecommitsforapullrequest
            res = await self.api("2", "get", "/user/permissions/teams", **kwargs)
            # teams.extend([group['team']['username'] for group in res['values']])
            for groups in res["values"]:
                team = groups["team"]
                teams.append(
                    dict(
                        name=team["display_name"],
                        id=team["uuid"][1:-1],
                        email=None,
                        username=team["username"],
                    )
                )

            if not res.get("next"):
                break
            url = res["next"]
            parsed = urlparse.urlparse(url)
            page = urlparse.parse_qs(parsed.query)["page"][0]

        return teams

    async def get_pull_request_commits(self, pullid, token=None):
        commits, page = [], None
        while True:
            # https://confluence.atlassian.com/bitbucket/pullrequests-resource-423626332.html#pullrequestsResource-GETthecommitsforapullrequest
            if page is not None:
                kwargs = dict(page=page, token=token)
            else:
                kwargs = dict(token=token)
            res = await self.api(
                "2",
                "get",
                "/repositories/%s/pullrequests/%s/commits" % (self.slug, pullid),
                **kwargs,
            )
            commits.extend([c["hash"] for c in res["values"]])
            if not res.get("next"):
                break
            url = res["next"]
            parsed = urllib_parse.urlparse(url)
            page = urllib_parse.parse_qs(parsed.query)["page"][0]
        return commits

    async def list_repos(self, username=None, token=None):
        """
        Lists all repositories a user is part of.
        *Note: 
        Bitbucket API V2 does not provide a dedicated endpoint which returns all repos a user is part of.
        It provides however, an endpoint to get all the repos a user is part of from an specific org or user.
        Endpoint to list repos from an specific user:
            - /repositories/{username}
        In order to get all the repositories a user is part of, we first need to get all the orgs and repo owners
        - Orgs/Teams can be obtained using the 'list_teams' method
        - Usernames of repo owners is a bit tricky since Bitbucket doesnt provide an endpoint for this
            - Solution: 
                Use the 'list_permissions' method to get all repo permissions and exctract owner's username 
                from the repository 'full_name' attribute
        Once we have all orgs/teams and owner's usernames we should call "/repositories/{username}" endpoint
        for each of the orgs/teams and owner's usernames.
        """
        data, page = [], 0
        # if username is not provided, list all repos
        if username is None:
            # get all teams a user is member of
            teams = await self.list_teams(token)
            usernames = set([team["username"] for team in teams])
            # get permission of all repositories a user is member of
            permissions = await self.list_permissions(token=token)
            # get repo owners
            for permission in permissions:
                repo = permission["repository"]
                name = repo["full_name"].split("/")
                usernames.add(name[0])
            # add user's own username
            usernames.add(self.data["owner"]["username"])
        else:
            usernames = [username]
        # fetch repo information
        for team in usernames:
            while True:
                page += 1
                # https://confluence.atlassian.com/display/BITBUCKET/repositories+Endpoint#repositoriesEndpoint-GETalistofrepositoriesforanaccount
                res = await self.api(
                    "2", "get", "/repositories/%s" % (team), page=page, token=token
                )
                if len(res["values"]) == 0:
                    page = 0
                    break
                for repo in res["values"]:
                    repo_name_arr = repo["full_name"].split("/", 1)

                    data.append(
                        dict(
                            owner=dict(
                                service_id=repo["owner"]["uuid"][1:-1],
                                username=repo_name_arr[0],
                            ),
                            repo=dict(
                                service_id=repo["uuid"][1:-1],
                                name=repo_name_arr[1],
                                language=self._validate_language(repo["language"]),
                                private=repo["is_private"],
                                branch="master",
                                fork=None,
                            ),
                        )
                    )
                if not res.get("next"):
                    page = 0
                    break
        return data

    async def list_permissions(self, token=None):
        data, page = [], 0
        while True:
            page += 1
            res = await self.api(
                "2", "get", "/user/permissions/repositories", page=page, token=token
            )
            if len(res["values"]) == 0:
                page = 0
                break
            for permission in res["values"]:
                data.append(permission)

            if not res.get("next"):
                page = 0
                break
        return data

    async def get_pull_request(self, pullid, token=None):
        # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource#pullrequestsResource-GETaspecificpullrequest
        try:
            res = await self.api(
                "2",
                "get",
                "/repositories/{}/pullrequests/{}".format(self.slug, pullid),
                token=token,
            )
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    ce.response, f"PR with id {pullid} does not exist"
                )
            raise
        # the commit sha is only {12}. need to get full sha
        base = await self.api(
            "2",
            "get",
            "/repositories/{}/commit/{}".format(
                self.slug, res["destination"]["commit"]["hash"]
            ),
            token=token,
        )
        head = await self.api(
            "2",
            "get",
            "/repositories/{}/commit/{}".format(
                self.slug, res["source"]["commit"]["hash"]
            ),
            token=token,
        )
        return dict(
            author=dict(
                id=str(res["author"]["uuid"][1:-1]) if res["author"] else None,
                username=res["author"].get("username") if res["author"] else None,
            ),
            base=dict(
                branch=res["destination"]["branch"]["name"], commitid=base["hash"]
            ),
            head=dict(branch=res["source"]["branch"]["name"], commitid=head["hash"]),
            state={"OPEN": "open", "MERGED": "merged", "DECLINED": "closed"}.get(
                res["state"]
            ),
            title=res["title"],
            id=str(pullid),
            number=str(pullid),
        )

    async def post_comment(self, issueid, body, token=None):
        # https://confluence.atlassian.com/display/BITBUCKET/issues+Resource#issuesResource-POSTanewcommentontheissue
        res = await self.api(
            "2",
            "post",
            "/repositories/%s/pullrequests/%s/comments" % (self.slug, issueid),
            body=dict(content=dict(raw=body)),
            json=True,
            token=token,
        )
        return res

    async def edit_comment(self, issueid, commentid, body, token=None):
        # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource+1.0#pullrequestsResource1.0-PUTanupdateonacomment
        # await self.api('1', 'put', '/repositories/%s/pullrequests/%s/comments/%s' % (self.slug, issueid, commentid),
        #                body=dict(content=body), token=token)
        try:
            res = await self.api(
                "2",
                "put",
                f"/repositories/{self.slug}/pullrequests/{issueid}/comments/{commentid}",
                body=dict(content=dict(raw=body)),
                json=True,
                token=token,
            )
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    ce.response,
                    f"Comment {commentid} from PR {issueid} cannot be found",
                )
            raise
        return res

    async def delete_comment(self, issueid, commentid, token=None):
        # https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D/%7Brepo_slug%7D/pullrequests/%7Bpull_request_id%7D/comments/%7Bcomment_id%7D
        try:
            await self.api(
                "2",
                "delete",
                "/repositories/%s/pullrequests/%s/comments/%s"
                % (self.slug, issueid, commentid),
                token=token,
            )
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    ce.response,
                    f"Comment {commentid} from PR {issueid} cannot be found",
                )
            raise
        return True

    async def get_commit_status(self, commit, token=None):
        # https://confluence.atlassian.com/bitbucket/buildstatus-resource-779295267.html
        statuses = await self.get_commit_statuses(commit, _in_loop=True, token=token)
        return str(statuses)

    async def get_commit_statuses(self, commit, token=None, _in_loop=None):
        statuses, page = [], 0
        status_keys = dict(INPROGRESS="pending", SUCCESSFUL="success", FAILED="failure")
        while True:
            page += 1
            # https://api.bitbucket.org/2.0/repositories/atlassian/aui/commit/d62ae57/statuses
            res = await self.api(
                "2",
                "get",
                "/repositories/%s/commit/%s/statuses" % (self.slug, commit),
                page=page,
                token=token,
            )
            _statuses = res["values"]
            if len(_statuses) == 0:
                break
            statuses.extend(
                [
                    {
                        "time": s["updated_on"],
                        "state": status_keys.get(s["state"]),
                        "description": s["description"],
                        "url": s["url"],
                        "context": s["key"],
                    }
                    for s in _statuses
                ]
            )
            if not res.get("next"):
                break
        return Status(statuses)

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
        # https://confluence.atlassian.com/bitbucket/buildstatus-resource-779295267.html
        status = dict(
            pending="INPROGRESS", success="SUCCESSFUL", error="FAILED", failure="FAILED"
        ).get(status)
        assert status, "status not valid"
        try:
            res = await self.api(
                "2",
                "post",
                "/repositories/%s/commit/%s/statuses/build" % (self.slug, commit),
                body=dict(
                    state=status,
                    key="codecov-" + context,
                    name=context.replace("/", " ").capitalize() + " Coverage",
                    url=url,
                    description=description,
                ),
                token=token,
            )
        except Exception:
            res = await self.api(
                "2",
                "put",
                "/repositories/%s/commit/%s/statuses/build/codecov-%s"
                % (self.slug, commit, context),
                body=dict(
                    state=status,
                    name=context.replace("/", " ").capitalize() + " Coverage",
                    url=url,
                    description=description,
                ),
                token=token,
            )

        if merge_commit:
            try:
                res = await self.api(
                    "2",
                    "post",
                    "/repositories/%s/commit/%s/statuses/build"
                    % (self.slug, merge_commit[0]),
                    body=dict(
                        state=status,
                        key="codecov-" + merge_commit[1],
                        name=merge_commit[1].replace("/", " ").capitalize()
                        + " Coverage",
                        url=url,
                        description=description,
                    ),
                    token=token,
                )
            except Exception:
                res = await self.api(
                    "2",
                    "put",
                    "/repositories/%s/commit/%s/statuses/build/codecov-%s"
                    % (self.slug, merge_commit[0], context),
                    body=dict(
                        state=status,
                        name=merge_commit[1].replace("/", " ").capitalize()
                        + " Coverage",
                        url=url,
                        description=description,
                    ),
                    token=token,
                )
        # check if the commit is a Merge
        return res

    async def get_commit(self, commit, token=None):
        # https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Bworkspace%7D/%7Brepo_slug%7D/commit/%7Bnode%7D
        try:
            data = await self.api(
                "2",
                "get",
                "/repositories/%s/commit/%s" % (self.slug, commit),
                token=token,
            )
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    ce.response, f"Commit {commit} cannot be found"
                )
            raise
        username = data["author"].get("user", {}).get("nickname")
        author_raw = (
            data["author"].get("raw", "")[:-1].rsplit(" <", 1)
            if " <" in data["author"].get("raw", "")
            else None
        )

        userid = data["author"].get("user", {}).get("uuid", "")[1:-1] or None

        # We used to look up the userid from the username if no uuid provided but
        # BitBucket has deprecated the '/users/{username}' endpoint for privacy reasons so we
        # have to use '/users/{account_id}' instead
        # https://developer.atlassian.com/bitbucket/api/2/reference/resource/users/%7Busername%7D
        account_id = data["author"].get("user", {}).get("account_id")
        if not userid and account_id:
            res = await self.api("2", "get", "/users/%s" % account_id, token=token)
            userid = res["uuid"][1:-1]

        return dict(
            author=dict(
                id=userid,
                username=username,
                name=author_raw[0] if author_raw else None,
                email=author_raw[1] if author_raw else None,
            ),
            commitid=commit,
            parents=[p["hash"] for p in data["parents"]],
            message=data["message"],
            timestamp=data["date"],
        )

    async def get_branches(self, token=None):
        # https://confluence.atlassian.com/display/BITBUCKET/repository+Resource+1.0#repositoryResource1.0-GETlistofbranches
        res = await self.api(
            "2",
            "get",
            "/repositories/%s/refs/branches" % self.slug,
            token=token,
            pagelen="100",
        )
        return [(k["name"], k["target"]["hash"]) for k in res["values"]]

    async def get_pull_requests(self, state="open", token=None):
        state = {"open": "OPEN", "merged": "MERGED", "close": "DECLINED"}.get(state)
        pulls, page = [], 0
        while True:
            page += 1
            # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource#pullrequestsResource-GETalistofopenpullrequests
            res = await self.api(
                "2",
                "get",
                "/repositories/%s/pullrequests" % self.slug,
                state=state,
                page=page,
                token=token,
            )
            if len(res["values"]) == 0:
                break
            pulls.extend([pull["id"] for pull in res["values"]])
            if not res.get("next"):
                break
        return pulls

    async def find_pull_request(
        self, commit=None, branch=None, state="open", token=None
    ):
        state = {"open": "OPEN", "merged": "MERGED", "close": "DECLINED"}.get(state, "")
        pulls, page = [], 0
        if commit or branch:
            while True:
                page += 1
                # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource#pullrequestsResource-GETalistofopenpullrequests
                res = await self.api(
                    "2",
                    "get",
                    "/repositories/%s/pullrequests" % self.slug,
                    state=state,
                    page=page,
                    token=token,
                )
                _prs = res["values"]
                if len(_prs) == 0:
                    break

                if commit:
                    for pull in _prs:
                        if commit.startswith(pull["source"]["commit"]["hash"]):
                            return str(pull["id"])
                else:
                    for pull in _prs:
                        if pull["source"]["branch"]["name"] == branch:
                            return str(pull["id"])

                if not res.get("next"):
                    break

    async def get_repository(self, token=None):
        if self.data["repo"].get("service_id") is None:
            # https://confluence.atlassian.com/display/BITBUCKET/repository+Resource#repositoryResource-GETarepository
            res = await self.api("2", "get", "/repositories/" + self.slug, token=token)
        else:
            res = await self.api(
                "2",
                "get",
                "/repositories/%%7B%s%%7D/%%7B%s%%7D"
                % (self.data["owner"]["service_id"], self.data["repo"]["service_id"]),
                token=token,
            )
        username, repo = tuple(res["full_name"].split("/", 1))
        return dict(
            owner=dict(service_id=res["owner"]["uuid"][1:-1], username=username),
            repo=dict(
                service_id=res["uuid"][1:-1],
                private=res["is_private"],
                branch="master",
                language=self._validate_language(res["language"]),
                name=repo,
            ),
        )

    async def get_authenticated(self, token=None):
        if self.data["repo"].get("private"):
            # https://confluence.atlassian.com/bitbucket/repository-resource-423626331.html#repositoryResource-GETarepository
            await self.api("2", "get", "/repositories/" + self.slug, token=token)
            return (True, True)
        else:
            # https://developer.atlassian.com/bitbucket/api/2/reference/resource/user/permissions/teams
            groups = await self.api(
                "2",
                "get",
                "/user/permissions/teams",
                token=token,
                q='team.uuid="{' + self.data["owner"]["service_id"] + '}"',
            )

            if groups["values"]:
                for group in groups["values"]:
                    if self.data["owner"]["username"] == group["team"]["username"]:
                        return (True, True)

            return (True, False)

    async def get_source(self, path, ref, token=None):
        # https://confluence.atlassian.com/bitbucket/src-resources-296095214.html
        try:
            src = await self.api(
                "2",
                "get",
                "/repositories/{0}/src/{1}/{2}".format(
                    self.slug, ref, path.replace(" ", "%20")
                ),
                token=token,
            )
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(
                    ce.response, f"Path {path} not found at {ref}"
                )
            raise
        return dict(commitid=None, content=src.decode())

    async def get_compare(
        self, base, head, context=None, with_commits=True, token=None
    ):
        # https://developer.atlassian.com/bitbucket/api/2/reference/resource/snippets/%7Busername%7D/%7Bencoded_id%7D/%7Brevision%7D/diff%C2%A0%E2%80%A6
        # https://api.bitbucket.org/2.0/repositories/markadams-atl/test-repo/diff/1b03803..fcba34b
        # IMPORANT it is reversed
        diff = await self.api(
            "2",
            "get",
            "/repositories/%s/diff/%s..%s" % (self.slug, head, base),
            context=context or 0,
            token=token,
        )

        commits = []
        if with_commits:
            commits = [{"commitid": head}, {"commitid": base}]
            # No endpoint to get commits yet... ugh

        return dict(diff=self.diff_to_json(diff.decode("utf8")), commits=commits)

    async def get_commit_diff(self, commit, context=None, token=None):
        # https://confluence.atlassian.com/bitbucket/diff-resource-425462484.html
        diff = await self.api(
            "2",
            "get",
            "/repositories/"
            + self.data["owner"]["username"]
            + "/"
            + self.data["repo"]["name"]
            + "/diff/"
            + commit,
            token=token,
        )
        return self.diff_to_json(diff.decode("utf8"))

    async def list_top_level_files(self, ref, token=None):
        return await self.list_files(ref, dir_path="", token=None)

    async def list_files(self, ref, dir_path, token=None):
        page = None
        has_more = True
        files = []
        while has_more:
            # https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D/%7Brepo_slug%7D/src#get
            if page is not None:
                kwargs = dict(page=page, token=token)
            else:
                kwargs = dict(token=token)
            results = await self.api(
                "2", "get", f"/repositories/{self.slug}/src/{ref}/{dir_path}", **kwargs
            )
            files.extend(results["values"])
            if "next" in results:
                url = results["next"]
                parsed = urllib_parse.urlparse(url)
                page = urllib_parse.parse_qs(parsed.query)["page"][0]
            else:
                has_more = False
        return [
            {"path": f["path"], "type": self._bitbucket_type_to_torngit_type(f["type"])}
            for f in files
        ]

    def _bitbucket_type_to_torngit_type(self, val):
        if val == "commit_file":
            return "file"
        elif val == "commit_directory":
            return "folder"
        return "other"

    async def get_ancestors_tree(self, commitid, token=None):
        res = await self.api(
            "2",
            "get",
            "/repositories/%s/commits" % self.slug,
            token=token,
            include=commitid,
        )
        start = res["values"][0]["hash"]
        commit_mapping = {
            val["hash"]: [k["hash"] for k in val["parents"]] for val in res["values"]
        }
        return self.build_tree_from_commits(start, commit_mapping)

    def get_external_endpoint(self, endpoint: Endpoints, **kwargs):
        if endpoint == Endpoints.commit_detail:
            return self.urls["commit"].format(
                username=self.data["owner"]["username"],
                name=self.data["repo"]["name"],
                commitid=kwargs["commitid"],
            )
        raise NotImplementedError()
