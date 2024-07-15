import base64
import logging
import os
from datetime import datetime
from json import dumps, loads
from typing import List
from urllib.parse import parse_qsl

import oauth2 as oauth
from tlslite.utils import keyfactory

from shared.config import (
    MissingConfigException,
    get_config,
    load_file_from_path_at_config,
)
from shared.torngit.base import TorngitBaseAdapter
from shared.torngit.exceptions import (
    TorngitClientError,
    TorngitClientGeneralError,
    TorngitObjectNotFoundError,
)
from shared.torngit.status import Status
from shared.utils.urls import url_concat

log = logging.getLogger(__name__)


class _Signature(oauth.SignatureMethod):
    name = "RSA-SHA1"
    privkey = None

    def _prepare_private_key():
        # The user should provide a path to a pemfile in `bitbucket_server.pemfile`
        try:
            pemfile = load_file_from_path_at_config("bitbucket_server", "pemfile")
        except MissingConfigException:
            log.exception("`bitbucket_server.pemfile` config required but not found")
            raise
        except FileNotFoundError:
            log.exception(
                "No PEM file found at configured path (`bitbucket_server.pemfile`)",
                extra=dict(path=get_config("bitbucket_server", "pemfile")),
            )
            raise

        # Parse and memoize the pemfile, if it's valid
        try:
            _Signature.privkey = keyfactory.parsePrivateKey(pemfile)
        except Exception as e:
            log.exception("Failed to parse PEM file", extra=dict(exception=e))
            raise

    def signing_base(self, request, consumer, token):
        if not hasattr(request, "normalized_url") or request.normalized_url is None:
            raise ValueError("Base URL for request is not set.")

        sig = (
            oauth.escape(request.method),
            oauth.escape(request.normalized_url),
            oauth.escape(request.get_normalized_parameters()),
        )
        # ('POST',
        # 'http%3A%2F%2Flocalhost%3A7990%2Fplugins%2Fservlet%2Foauth%2Frequest-token',
        # 'oauth_consumer_key%3DjFzYB8pKJnz2BhaDUw%26oauth_nonce%3D15620364%26oauth_signature_method%3DRSA-SHA1%26oauth_timestamp%3D1442832674%26oauth_version%3D1.0')

        key = "%s&" % oauth.escape(consumer.secret)
        if token:
            key += oauth.escape(token.secret)
        raw = "&".join(sig)
        return key, raw.encode()

    def sign(self, request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.signing_base(request, consumer, token)

        # If this is the first time we're signing a request, initialize the private key
        if not _Signature.privkey:
            _Signature._prepare_private_key()
            assert _Signature.privkey, "Failed to load private key to sign requests"

        signature = _Signature.privkey.hashAndSign(raw)
        return base64.b64encode(signature)


signature = _Signature()


class BitbucketServer(TorngitBaseAdapter):
    # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html
    service = "bitbucket_server"

    @classmethod
    def get_service_url(cls):
        return get_config("bitbucket_server", "url")

    @property
    def service_url(self):
        return self.get_service_url()

    urls = dict(
        user="users/%(username)s",
        owner="projects/%(username)s",
        repo="projects/%(username)s/repos/%(name)s",
        issues="projects/%(username)s/repos/%(name)s/issues/%(issueid)s",
        commit="projects/%(username)s/repos/%(name)s/commits/%(commitid)s",
        commits="projects/%(username)s/repos/%(name)s/commits",
        src="projects/%(username)s/repos/%(name)s/browse/%(path)s?at=%(commitid)s",
        tree="projects/%(username)s/repos/%(name)s/browse?at=%(commitid)s",
        create_file=None,
        branch="projects/%(username)s/repos/%(name)s/browser?at=%(branch)s",
        pull="projects/%(username)s/repos/%(name)s/pull-requests/%(pullid)s/overview",
        compare="",
    )

    @property
    def project(self):
        if self.data["owner"].get("service_id", "?")[0] == "U":
            return "/projects/~%s" % self.data["owner"]["username"].upper()
        else:
            return "/projects/%s" % self.data["owner"]["username"].upper()

    def diff_to_json(self, diff_json):
        results = {}
        for _diff in diff_json:
            if not _diff.get("destination"):
                results[_diff["source"]["toString"]] = dict(type="deleted")

            else:
                fname = _diff["destination"]["toString"]
                _before = _diff["source"]["toString"] if _diff.get("source") else None
                _file = results.setdefault(
                    fname,
                    dict(
                        before=_before if _before != fname else None,
                        type="new" if _before is None else "modified",
                        segments=[],
                    ),
                )
                for hunk in _diff.get("hunks", []):
                    segment = dict(
                        header=[
                            str(hunk["sourceLine"]),
                            str(hunk["sourceSpan"]),
                            str(hunk["destinationLine"]),
                            str(hunk["destinationSpan"]),
                        ],
                        lines=[],
                    )
                    _file["segments"].append(segment)
                    for seg in hunk["segments"]:
                        t = seg["type"][0]
                        for ln in seg["lines"]:
                            segment["lines"].append(
                                ("-" if t == "R" else "+" if t == "A" else " ")
                                + ln["line"]
                            )

        if results:
            return dict(files=self._add_diff_totals(results))
        else:
            return dict(files=[])

    async def api(self, method, url, body=None, token=None, **kwargs):
        # process desired api path
        if not url.startswith("http"):
            url = "%s/rest/api/1.0%s" % (self.service_url, url)

        # process inline arguments
        if kwargs:
            url = url_concat(url, kwargs)

        # get accessing token
        if token:
            token = oauth.Token(token["key"], token["secret"])
        elif self.token:
            token = oauth.Token(self.token["key"], self.token["secret"])
        else:
            token = None

        # create oauth consumer
        if self.verify_ssl is False:
            # https://github.com/joestump/python-oauth2/blob/9d5a569fc9edda678102edccb330e1f692122a5a/oauth2/__init__.py#L627
            # https://github.com/jcgregorio/httplib2/blob/e7f6e622047107e701ee70e7ec586717d97b0cbb/python2/httplib2/__init__.py#L1158
            verify_ssl = dict(disable_ssl_certificate_validation=True, ca_certs=False)
        elif self.verify_ssl:
            verify_ssl = dict(ca_certs=self.verify_ssl)
        else:
            verify_ssl = dict(ca_certs=os.getenv("REQUESTS_CA_BUNDLE"))

        client = oauth.Client(
            oauth.Consumer(self._oauth_consumer_token()["key"], ""), token, **verify_ssl
        )
        client.set_signature_method(signature)

        response, content = client.request(
            url,
            method.upper(),
            dumps(body).encode() if body else b"",
            headers={"Content-Type": "application/json"} if body else {},
        )
        status = int(response["status"])

        if status in (200, 201):
            if "application/json" in response.get("content-type"):
                return loads(content)
            else:
                try:
                    content = dict(parse_qsl(content)) or content
                except Exception:
                    pass

                return content

        elif status == 204:
            return None

        message = f"BitBucket Server API: {status}"
        raise TorngitClientGeneralError(status, response_data=response, message=message)

    async def get_authenticated(self, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp1889424
        if self.data["repo"]["private"]:
            await self.api(
                "get",
                "%s/repos/%s" % (self.project, self.data["repo"]["name"]),
                token=token,
            )
        return (True, True)

    async def get_is_admin(self, user, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3389568
        res = await self.api(
            "get",
            "%s/permissions/users" % self.project,
            filter=user["username"],
            token=token,
        )
        userid = str(user["service_id"]).replace("U", "")
        # PROJECT_READ, PROJECT_WRITE, PROJECT_ADMIN, ADMIMN
        res = any(
            filter(
                lambda v: str(v["user"]["id"]) == userid and "ADMIN" in v["permission"],
                res["values"],
            )
        )
        return res

    async def get_repository(self, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp1889424
        res = await self.api(
            "get",
            "%s/repos/%s" % (self.project, self.data["repo"]["name"]),
            token=token,
        )
        owner_service_id = res["project"]["id"]
        if res["project"]["type"] == "PERSONAL":
            owner_service_id = "U%d" % res["project"]["owner"]["id"]

        fork = None
        if res.get("origin"):
            _fork_owner_service_id = res["origin"]["project"]["id"]
            if res["origin"]["project"]["type"] == "PERSONAL":
                _fork_owner_service_id = "U%d" % res["origin"]["project"]["owner"]["id"]

            fork = dict(
                owner=dict(
                    service_id=_fork_owner_service_id,
                    username=res["origin"]["project"]["key"],
                ),
                repo=dict(
                    service_id=res["origin"]["id"],
                    language=None,
                    private=(not res["origin"]["public"]),
                    branch="main",
                    fork=fork,
                    name=res["origin"]["slug"],
                ),
            )

        return dict(
            owner=dict(service_id=owner_service_id, username=res["project"]["key"]),
            repo=dict(
                service_id=res["id"],
                language=None,
                private=(not res.get("public", res.get("origin", {}).get("public"))),
                branch="main",
                name=res["slug"],
            ),
        )

    async def get_repo_languages(self, token=None, language: str = None) -> List[str]:
        """
        Gets the languages belonging to this repository. Bitbucket has no way to
        track languages, so we'll return a list with the existing language
        Param:
            language: the language belonging to the repository.language key
        Returns:
            List[str]: A list of language names
        """
        languages = []

        if language:
            languages.append(language.lower())

        return languages

    async def get_source(self, path, ref, token=None):
        content, start = [], 0
        while True:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2028128
            try:
                res = await self.api(
                    "get",
                    "{0}/repos/{1}/browse/{2}".format(
                        self.project,
                        self.data["repo"]["name"],
                        path.replace(" ", "%20"),
                    ),
                    at=ref,
                    start=start,
                    token=token,
                )
            except TorngitClientError as ce:
                if ce.code == 404:
                    raise TorngitObjectNotFoundError(
                        response_data=ce.response_data,
                        message=f"Path {path} not found at {ref}",
                    )
                raise

            content.extend(res["lines"])
            if res["isLastPage"] or res.get("nextPageStart") is None:
                break
            else:
                start = res["nextPageStart"]

        return dict(
            commitid=None,  # [FUTURE] unknown atm
            content="\n".join(map(lambda a: a.get("text", ""), content)),
        )

    async def get_ancestors_tree(self, commitid, token=None):
        res = await self.api(
            "get",
            "%s/repos/%s/commits/" % (self.project, self.data["repo"]["name"]),
            token=token,
            until=commitid,
        )
        start = res["values"][0]["id"]
        commit_mapping = {
            val["id"]: [k["id"] for k in val["parents"]] for val in res["values"]
        }
        return self.build_tree_from_commits(start, commit_mapping)

    async def get_commit(self, commit, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3530560
        res = await self.api(
            "get",
            "%s/repos/%s/commits/%s"
            % (self.project, self.data["repo"]["name"], commit),
            token=token,
        )

        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2598928
        author = await self.api(
            "get", "/users", filter=res["author"]["emailAddress"], token=token
        )
        if not author["size"]:
            author = await self.api("get", "/users", filter=res["author"]["name"])
        author = author["values"][0] if author["size"] else {}

        return dict(
            author=dict(
                id=("U%s" % author.get("id")) if author.get("id") else None,
                username=author.get("name"),
                email=res["author"]["emailAddress"],
                name=res["author"]["name"],
            ),
            commitid=commit,
            parents=[p["id"] for p in res["parents"]],
            message=res["message"],
            timestamp=datetime.fromtimestamp(
                int(str(res["authorTimestamp"])[:10])
            ).strftime("%Y-%m-%d %H:%M:%S"),
        )

    async def get_pull_request_commits(self, pullid, token=None, _in_loop=None):
        commits, start = [], 0
        while True:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2519392
            res = await self.api(
                "get",
                "%s/repos/%s/pull-requests/%s/commits"
                % (self.project, self.data["repo"]["name"], pullid),
                start=start,
                token=token,
            )
            if len(res["values"]) == 0:
                break
            commits.extend([c["id"] for c in res["values"]])
            if res["isLastPage"] or res.get("nextPageStart") is None:
                break
            else:
                start = res["nextPageStart"]

        # order is NEWEST...OLDEST
        return commits

    async def get_commit_diff(self, commit, context=None, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3120016
        diff = await self.api(
            "get",
            "%s/repos/%s/commits/%s/diff"
            % (self.project, self.data["repo"]["name"], commit),
            withComments=False,
            whitespace="ignore-all",
            contextLines=context or -1,
            token=None,
        )
        return self.diff_to_json(diff["diffs"])

    async def get_compare(
        self, base, head, context=None, with_commits=True, token=None
    ):
        # get diff
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3370768
        diff = (
            await self.api(
                "get",
                "%s/repos/%s/commits/%s/diff"
                % (self.project, self.data["repo"]["name"], head),
                withComments=False,
                whitespace="ignore-all",
                contextLines=context or -1,
                since=base,
                token=token,
            )
        )["diffs"]

        # get commits
        commits, start = [], 0
        while with_commits:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3513104
            res = await self.api(
                "get",
                "%s/repos/%s/commits" % (self.project, self.data["repo"]["name"]),
                start=start,
                token=token,
                since=base,
                until=head,
            )
            #  listed [newest...oldest]
            commits.extend(
                [
                    dict(
                        commitid=c["id"],
                        message=c["message"],
                        timestamp=c["authorTimestamp"],
                        author=dict(
                            name=c["author"]["name"], email=c["author"]["emailAddress"]
                        ),
                    )
                    for c in res["values"]
                ]
            )
            if res["isLastPage"] or res.get("nextPageStart") is None:
                break
            else:
                start = res["nextPageStart"]

        return dict(diff=self.diff_to_json(diff), commits=commits[::-1])

    async def post_webhook(self, name, url, events, secret, token=None):
        # https://docs.atlassian.com/bitbucket-server/rest/6.0.1/bitbucket-rest.html#idp325
        # https://confluence.atlassian.com/bitbucketserver066/event-payload-978197889.html
        res = await self.api(
            "post",
            "%s/repos/%s/webhooks" % (self.project, self.data["repo"]["name"]),
            body=dict(description=name, active=True, events=events, url=url),
            json=True,
            token=token,
        )
        return res

    async def get_pull_request(self, pullid, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2167824
        res = await self.api(
            "get",
            "%s/repos/%s/pull-requests/%s"
            % (self.project, self.data["repo"]["name"], pullid),
            token=token,
        )
        # need to get all commits, shit.
        pull_commitids = await self.get_pull_request_commits(
            pullid, token=token, _in_loop=True
        )
        first_commit = (
            await self.api(
                "get",
                "%s/repos/%s/commits/%s"
                % (self.project, self.data["repo"]["name"], pull_commitids[-1]),
                token=token,
            )
        )["parents"][0]["id"]
        return dict(
            title=res["title"],
            state={"OPEN": "open", "DECLINED": "close", "MERGED": "merged"}.get(
                res["state"]
            ),
            id=str(pullid),
            number=str(pullid),
            base=dict(branch=res["toRef"]["displayId"], commitid=first_commit),
            head=dict(branch=res["fromRef"]["displayId"], commitid=pull_commitids[0]),
        )

    async def list_top_level_files(self, ref, token=None):
        return await self.list_files(ref, dir_path="", token=None)

    async def list_files(self, ref, dir_path, token=None):
        page = None
        has_more = True
        files = []
        while has_more:
            # https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D/%7Brepo_slug%7D/src#get
            kwargs = {}

            if page is not None:
                kwargs["page"] = page

            if ref not in [None, ""]:
                kwargs["at"] = ref

            results = await self.api(
                "get",
                "%s/repos/%s/files/%s"
                % (self.project, self.data["repo"]["name"], dir_path),
                **kwargs,
            )
            files.extend(results["values"])
            page = results["nextPageStart"]
            has_more = not results["isLastPage"]
        return [{"path": f, "type": "file"} for f in files]

    async def _fetch_page_of_repos(self, start, token):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp1847760
        res = await self.api("get", "/repos", start=start, token=token)

        repos = []
        for repo in res["values"]:
            ownerid = str(repo["project"]["id"])
            if repo["project"]["type"] == "PERSONAL":
                ownerid = "U" + str(repo["project"]["owner"]["id"])

            repos.append(
                dict(
                    owner=dict(
                        service_id=ownerid,
                        username=repo["project"]["key"].lower().replace("~", ""),
                    ),
                    repo=dict(
                        service_id=repo["id"],
                        name=repo["slug"].lower(),
                        language=None,
                        private=(
                            not repo.get("public", repo.get("origin", {}).get("public"))
                        ),
                        branch="main",
                    ),
                )
            )

        next_page_start = res.get("nextPageStart") if not res["isLastPage"] else None
        return (repos, next_page_start)

    async def list_repos(self, username=None, token=None):
        data, start = [], 0
        while True:
            repos, next_page_start = await self._fetch_page_of_repos(start, token)

            if len(repos) == 0 or next_page_start is None:
                break
            else:
                start = next_page_start

        return data

    async def list_repos_generator(self, username=None, token=None):
        """
        New version of list_repos() that should replace the old one after safely
        rolling out in the worker.
        """
        start = 0
        while True:
            repos, next_page_start = await self._fetch_page_of_repos(start, token)

            if len(repos) == 0:
                break

            yield repos

            if next_page_start is None:
                break
            else:
                start = next_page_start

    async def list_teams(self, token=None):
        data, start = [], 0
        while True:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2301216
            res = await self.api("get", "/projects", start=start, token=token)
            if len(res["values"]) == 0:
                break
            data.extend(
                [
                    dict(id=row["id"], username=row["key"], name=row["name"])
                    for row in res["values"]
                ]
            )
            if res["isLastPage"] or res.get("nextPageStart") is None:
                break
            else:
                start = res["nextPageStart"]

        return data

    async def get_commit_statuses(self, commit, _merge=None, token=None):
        # https://developer.atlassian.com/stash/docs/latest/how-tos/updating-build-status-for-commits.html
        start, data = 0, []
        while True:
            res = await self.api(
                "get",
                "%s/rest/build-status/1.0/commits/%s" % (self.service_url, commit),
                start=start,
                token=token,
            )
            if len(res["values"]) == 0:
                break
            data.extend(
                [
                    {
                        "time": s["dateAdded"],
                        "state": s["state"],
                        "url": s["url"],
                        "description": s["description"],
                        "context": s["name"],
                    }
                    for s in res["values"]
                ]
            )
            if res["isLastPage"] or res.get("nextPageStart") is None:
                break
            else:
                start = res["nextPageStart"]

        return Status(data)

    async def set_commit_status(
        self,
        commit,
        status,
        context,
        description,
        url=None,
        merge_commit=None,
        token=None,
        coverage=None,
    ):
        # https://developer.atlassian.com/stash/docs/latest/how-tos/updating-build-status-for-commits.html
        assert status in ("pending", "success", "error", "failure"), "status not valid"
        res = await self.api(
            "post",
            "%s/rest/build-status/1.0/commits/%s" % (self.service_url, commit),
            body=dict(
                state=dict(
                    pending="INPROGRESS",
                    success="SUCCESSFUL",
                    error="FAILED",
                    failure="FAILED",
                ).get(status),
                key=context,
                name=context,
                url=url,
                description=description,
            ),
            token=token,
        )
        if merge_commit:
            await self.api(
                "post",
                "%s/rest/build-status/1.0/commits/%s"
                % (self.service_url, merge_commit[0]),
                body=dict(
                    state=dict(
                        pending="INPROGRESS",
                        success="SUCCESSFUL",
                        error="FAILED",
                        failure="FAILED",
                    ).get(status),
                    key=merge_commit[1],
                    name=merge_commit[1],
                    url=url,
                    description=description,
                ),
                token=token,
            )
        return {"id": res.get("id", "NO-ID") if res else "NO-ID"}

    async def post_comment(self, pullid, body, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3165808
        res = await self.api(
            "post",
            "%s/repos/%s/pull-requests/%s/comments"
            % (self.project, self.data["repo"]["name"], pullid),
            body=dict(text=body),
            token=token,
        )
        return {"id": "%(id)s:%(version)s" % res}

    async def edit_comment(self, pullid, commentid, body, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3184624
        commentid, version = commentid.split(":", 1)
        res = await self.api(
            "put",
            "%s/repos/%s/pull-requests/%s/comments/%s"
            % (self.project, self.data["repo"]["name"], pullid, commentid),
            body=dict(text=body, version=version),
            token=token,
        )
        return {"id": "%(id)s:%(version)s" % res}

    async def delete_comment(self, issueid, commentid, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3189408
        commentid, version = commentid.split(":", 1)
        await self.api(
            "delete",
            "%s/repos/%s/pull-requests/%s/comments/%s"
            % (self.project, self.data["repo"]["name"], issueid, commentid),
            version=version,
            token=token,
        )
        return True

    async def get_branches(self, token=None):
        branches, start = [], 0
        while True:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2243696
            res = await self.api(
                "get",
                "%s/repos/%s/branches" % (self.project, self.data["repo"]["name"]),
                start=start,
                token=token,
            )
            if len(res["values"]) == 0:
                break
            branches.extend(
                [
                    (b["displayId"].encode("utf-8", "replace"), b["latestCommit"])
                    for b in res["values"]
                ]
            )
            if res["isLastPage"] or res.get("nextPageStart") is None:
                break
            else:
                start = res["nextPageStart"]
        return branches

    async def find_pull_request(
        self, commit=None, branch=None, state="open", token=None
    ):
        start = 0
        state = {"open": "OPEN", "close": "DECLINED", "merged": "MERGED"}.get(
            state, "ALL"
        )
        if branch:
            while True:
                # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2048560
                res = await self.api(
                    "get",
                    "%s/repos/%s/pull-requests"
                    % (self.project, self.data["repo"]["name"]),
                    state=state,
                    withAttributes=False,
                    withProperties=False,
                    start=start,
                    token=token,
                )
                if len(res["values"]) == 0:
                    break

                for pull in res["values"]:
                    if pull["fromRef"]["displayId"] == branch:
                        return pull["id"]

                if res["isLastPage"] or res.get("nextPageStart") is None:
                    break

                else:
                    start = res["nextPageStart"]

    async def get_pull_requests(self, state="open", token=None):
        pulls, start = [], 0
        state = {"open": "OPEN", "close": "DECLINED", "merged": "MERGED"}.get(
            state, "ALL"
        )
        while True:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2048560
            res = await self.api(
                "get",
                "%s/repos/%s/pull-requests" % (self.project, self.data["repo"]["name"]),
                state=state,
                withAttributes=False,
                withProperties=False,
                start=start,
                token=token,
            )
            if len(res["values"]) == 0:
                break
            pulls.extend([pull["id"] for pull in res["values"]])
            if res["isLastPage"] or res.get("nextPageStart") is None:
                break
            else:
                start = res["nextPageStart"]
        return pulls
