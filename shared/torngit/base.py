import re
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

import httpx

from shared.torngit.cache import torngit_cache
from shared.torngit.enums import Endpoints
from shared.typings.oauth_token_types import OauthConsumerToken, OnRefreshCallback

get_start_of_line = re.compile(r"@@ \-(\d+),?(\d*) \+(\d+),?(\d*).*").match


class TokenType(Enum):
    read = auto()
    admin = auto()
    comment = auto()
    status = auto()
    tokenless = auto()


class TorngitBaseAdapter(object):
    _repo_url: str = None
    _aws_key = None
    _oauth: OauthConsumerToken = None
    _on_token_refresh: OnRefreshCallback = None
    _token = None
    verify_ssl = None

    valid_languages = (
        "javascript",
        "shell",
        "python",
        "ruby",
        "perl",
        "dart",
        "java",
        "c",
        "clojure",
        "d",
        "fortran",
        "go",
        "groovy",
        "kotlin",
        "php",
        "r",
        "scala",
        "swift",
        "objective-c",
        "xtend",
    )

    def get_client(self, timeouts: List[int] = []) -> httpx.AsyncClient:
        if timeouts:
            timeout = httpx.Timeout(timeouts[1], connect=timeouts[0])
        else:
            timeout = httpx.Timeout(self._timeouts[1], connect=self._timeouts[0])
        return httpx.AsyncClient(
            verify=self.verify_ssl
            if not isinstance(self.verify_ssl, bool)
            else self.verify_ssl,
            timeout=timeout,
        )

    def get_token_by_type(self, token_type: TokenType):
        if self._token_type_mapping.get(token_type) is not None:
            return self._token_type_mapping.get(token_type)
        return self.token

    def get_token_by_type_if_none(self, token: Optional[str], token_type: TokenType):
        if token is not None:
            return token
        return self.get_token_by_type(token_type)

    def _oauth_consumer_token(self):
        if not self._oauth:
            raise Exception("Oauth consumer token not present")
        return self._oauth

    def __init__(
        self,
        oauth_consumer_token: OauthConsumerToken = None,
        timeouts=None,
        token=None,
        token_type_mapping: Dict[TokenType, Dict] = None,
        on_token_refresh: OnRefreshCallback = None,
        verify_ssl=None,
        **kwargs,
    ):
        self._timeouts = timeouts or [10, 30]
        self._token = token
        self._on_token_refresh = on_token_refresh
        self._token_type_mapping = token_type_mapping or {}
        self._oauth = oauth_consumer_token
        self.data = {"owner": {}, "repo": {}}
        self.verify_ssl = verify_ssl
        self.data.update(kwargs)
        # This has the side effect of initializing the torngit_cache
        # (if not yet initialized)
        torngit_cache.initialize()

    def __repr__(self):
        return "<%s slug=%s ownerid=%s repoid=%s>" % (
            self.service,
            self.slug,
            self.data["owner"].get("ownerid"),
            self.data["repo"].get("repoid"),
        )

    def _validate_language(self, language):
        if language:
            language = language.lower()
            if language in self.valid_languages:
                return language

    def set_token(self, token: OauthConsumerToken):
        self._token = token

    @property
    def token(self):
        if not self._token:
            self._token = self._oauth_consumer_token()
        return self._token

    @property
    def slug(self):
        if self.data.get("owner") and self.data.get("repo"):
            if self.data["owner"].get("username") and self.data["repo"].get("name"):
                return "%s/%s" % (
                    self.data["owner"]["username"],
                    self.data["repo"]["name"],
                )

    def build_tree_from_commits(self, start, commit_mapping):
        parents = []
        for p in commit_mapping.get(start, []):
            parents.append(self.build_tree_from_commits(p, commit_mapping))
        return {"commitid": start, "parents": parents}

    def diff_to_json(self, diff):
        """
        Processes a full diff (multiple files) into the object pattern below
        docs/specs/diff.json
        """
        results = {}
        diff = ("\n%s" % diff).split("\ndiff --git a/")
        segment = None
        for _diff in diff[1:]:
            _diff = _diff.replace("\r\n", "\n").split("\n")
            if _diff[-1] == "":
                # if the diff ends in a '\n' character then we'll have an extra
                # empty line at the end that we don't want
                _diff.pop()

            try:
                before, after = _diff.pop(0).split(" b/", 1)
            except IndexError:
                before, after = None, None
                # find the --- a
                for source in _diff:
                    if source.startswith("--- a/"):
                        before = source[6:]
                    elif source.startswith("+++ b/"):
                        after = source[6:]
                        break

            if after is None:
                continue

            # Is the file empty, skipped, etc
            # -------------------------------
            _file = dict(
                type="new" if before == "/dev/null" else "modified",
                before=None if before == after or before == "/dev/null" else before,
                segments=[],
            )

            results[after] = _file

            # Get coverage data on each line
            # ------------------------------
            # make file, this is ONE file not multiple
            for source in _diff:
                if re.match(r"\\ No newline at end of file", source):
                    continue

                sol4 = source[:4]
                if sol4 == "dele":
                    # deleted file mode 100644
                    _file["before"] = after
                    _file["type"] = "deleted"
                    _file.pop("segments")
                    break

                elif sol4 == "new " and not source.startswith("new mode "):
                    _file["type"] = "new"

                elif sol4 == "Bina":
                    _file["type"] = "binary"
                    _file.pop("before")
                    _file.pop("segments")
                    break

                elif sol4 in ("--- ", "+++ ", "inde", "diff", "old ", "new "):
                    # diff --git a/app/commit.py b/app/commit.py
                    # new file mode 100644
                    # index 0000000..d5ee3d6
                    # --- /dev/null
                    # +++ b/app/commit.py
                    continue

                elif sol4 == "@@ -":
                    # ex: "@@ -31,8 +31,8 @@ blah blah blah"
                    # ex: "@@ -0,0 +1 @@"
                    l = get_start_of_line(source).groups()
                    segment = dict(header=[l[0], l[1], l[2], l[3]], lines=[])
                    _file["segments"].append(segment)

                elif source == "":
                    continue

                elif segment:
                    # actual lines
                    segment["lines"].append(source)

                # else:
                #     results.pop(fname)
                #     break

        if results:
            return dict(files=self._add_diff_totals(results))

    def _add_diff_totals(self, diff):
        for fname, data in diff.items():
            rm = 0
            add = 0
            if "segments" in data:
                for segment in data["segments"]:
                    rm += sum([1 for line in segment["lines"] if line[0] == "-"])
                    add += sum([1 for line in segment["lines"] if line[0] == "+"])
            data["stats"] = dict(added=add, removed=rm)
        return diff

    # COMMENT LOGIC

    async def delete_comment(
        self, pullid: str, commentid: str, token: str = None
    ) -> bool:
        """Deletes a comment on a PR from the provider

        Args:
            pullid (str): The pull request identifier. If not str, will be stingified on the
                formatting of url
            commentid (str): The commend identifier
            token (str, optional): An optional token that can be used instead of the client default

        Raises:
            NotImplementedError: If the adapter does not have this ability implemented
            exceptions.ObjectNotFoundException: If this comment could not be found
            exceptions.TorngitClientError: If any other HTTP error occurs
        """
        raise NotImplementedError()

    async def post_comment(self, pullid: str, body: str, token=None) -> dict:
        raise NotImplementedError()

    async def edit_comment(
        self, pullid: str, commentid: str, body: str, token=None
    ) -> dict:
        raise NotImplementedError()

    # PULL REQUEST LOGIC

    async def find_pull_request(
        self, commit=None, branch=None, state="open", token=None
    ):
        raise NotImplementedError()

    async def get_pull_request(self, pullid: str, token=None):
        raise NotImplementedError()

    async def get_pull_request_commits(self, pullid: str, token=None):
        raise NotImplementedError()

    async def get_pull_requests(self, state="open", token=None):
        raise NotImplementedError()

    async def get_pull_request_files(self, pullid: str, token=None):
        raise NotImplementedError()

    # COMMIT LOGIC

    async def get_commit(self, commit: str, token=None):
        raise NotImplementedError()

    async def get_commit_diff(self, commit: str, context=None, token=None):
        raise NotImplementedError()

    async def get_commit_statuses(self, commit: str, _merge=None, token=None):
        raise NotImplementedError()

    async def set_commit_status(
        self,
        commit: str,
        status,
        context,
        description,
        url,
        coverage=None,
        merge_commit=None,
        token=None,
    ):
        raise NotImplementedError()

    # WEBHOOK LOGIC

    async def post_webhook(self, name, url, events: dict, secret, token=None) -> dict:
        raise NotImplementedError()

    async def delete_webhook(self, hookid: str, token=None):
        raise NotImplementedError()

    async def edit_webhook(
        self, hookid: str, name, url, events: dict, secret, token=None
    ) -> dict:
        raise NotImplementedError()

    # OTHERS

    async def get_authenticated(self, token=None) -> Tuple[bool, bool]:
        """Finds the user permissions about about whether the user on
            `self.data["user"]` can access the repo from `self.data["repo"]`
            Returns a `can_view` and a `can_edit` permission tuple

            IMPORTANT NOTE: As it is right now, this function will never return can_view=False
            It is either can_view=True, or raise 404 because from the user perspective, that
            repo does not exist.

            This kind of makes the first value of the result a bit useless

        Args:
            token (None, optional): Description

        Returns:`
            Tuple[bool, bool]: A tuple telling:

                can_view, can_edit

        """
        raise NotImplementedError()

    async def get_authenticated_user(self, **kwargs):
        raise NotImplementedError()

    async def get_branches(self, token=None):
        raise NotImplementedError()

    async def get_branch(self, token=None):
        raise NotImplementedError()

    async def get_compare(
        self, base, head, context=None, with_commits=True, token=None
    ):
        raise NotImplementedError()

    async def get_distance_in_commits(
        self, base_branch, base, context=None, with_commits=True, token=None
    ):
        return {
            "behind_by": None,
            "behind_by_commit": None,
            "status": None,
            "ahead_by": None,
        }

    async def get_is_admin(self, user: dict, token=None) -> bool:
        """Tells whether `user` is an admin of the organization described on `self.data`

        Args:
            user (dict): Description
            token (None, optional): Description
        """
        raise NotImplementedError()

    async def get_repository(self, token=None):
        raise NotImplementedError()

    async def get_source(self, path, ref, token=None):
        raise NotImplementedError()

    async def list_repos(self, username=None, token=None):
        raise NotImplementedError()

    async def list_teams(self, token=None):
        raise NotImplementedError()

    def get_external_endpoint(self, endpoint: Endpoints, **kwargs):
        raise NotImplementedError()

    async def list_files(self, ref: str, dir_path: str, token=None):
        raise NotImplementedError()

    def get_href(self, endpoint: Endpoints, **kwargs):
        path = self.get_external_endpoint(endpoint, **kwargs)
        return f"{self.service_url}/{path}"

    async def list_top_level_files(self, ref, token=None):
        """List the files on the top level of the repository

        Returns:
            list[dict] - A list of dicts, one for each file/directory on the top
                level of the repo. While different implementations might
                return a different set of values on each dict, the only keys you
                can safely expect from each dict are:

                - `path` - The path of the structure
                - `type` - The type: can be "folder" or "file" or "other"
        """
        raise NotImplementedError()

    async def get_workflow_run(self, run_id, token=None):
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
        raise NotImplementedError()
