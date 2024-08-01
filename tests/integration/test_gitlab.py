import pytest
import vcr
from prometheus_client import REGISTRY

from shared.torngit.enums import Endpoints
from shared.torngit.exceptions import TorngitClientError, TorngitObjectNotFoundError
from shared.torngit.gitlab import Gitlab


@pytest.fixture
def valid_handler():
    return Gitlab(
        repo=dict(service_id="187725", name="ci-repo"),
        owner=dict(username="codecov", service_id="109479"),
        token=dict(key=16 * "f882"),
    )


@pytest.fixture
def subgroup_handler():
    return Gitlab(
        repo=dict(service_id="187725", name="codecov-test"),
        owner=dict(username="group:subgroup1:subgroup2", service_id="7983213"),
        token=dict(key=16 * "f882"),
    )


@pytest.fixture
def admin_handler():
    return Gitlab(
        repo=dict(service_id="12060694"),
        owner=dict(username="codecov-organization", service_id="4037482"),
        token=dict(key=16 * "f882"),
    )


class TestGitlabTestCase(object):
    @pytest.mark.asyncio
    async def test_get_is_admin(self, admin_handler, codecov_vcr):
        user = dict(service_id="3108129")
        is_admin = await admin_handler.get_is_admin(
            user=user, token=dict(key=16 * "f882", username="hootener")
        )
        assert is_admin

    @pytest.mark.asyncio
    async def test_get_best_effort_branches(self, valid_handler, codecov_vcr):
        branches = await valid_handler.get_best_effort_branches(
            "c739768fcac68144a3a6d82305b9c4106934d31a"
        )
        assert branches == ["main", "other-branch"]

    @pytest.mark.asyncio
    async def test_post_comment(self, valid_handler, codecov_vcr):
        expected_result = {
            "id": 113977323,
            "noteable_id": 59639,
            "noteable_iid": 1,
            "noteable_type": "MergeRequest",
            "resolvable": False,
            "system": False,
            "type": None,
            "updated_at": "2018-11-02T05:25:09.363Z",
            "attachment": None,
            "author": {
                "avatar_url": "https://secure.gravatar.com/avatar/dcdb35375db567705dd7e74226fae67b?s=80&d=identicon",
                "name": "Codecov",
                "state": "active",
                "id": 109640,
                "username": "codecov",
                "web_url": "https://gitlab.com/codecov",
            },
            "body": "Hello world",
            "created_at": "2018-11-02T05:25:09.363Z",
        }
        res = await valid_handler.post_comment("1", "Hello world")
        assert res["author"] == expected_result["author"]
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_edit_comment(self, valid_handler, codecov_vcr):
        res = await valid_handler.edit_comment("1", "113977323", "Hello world number 2")
        assert res is not None
        assert res["id"] == 113977323

    @pytest.mark.asyncio
    async def test_edit_comment_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.edit_comment("1", 113979999, "Hello world number 2")

    @pytest.mark.asyncio
    async def test_delete_comment(self, valid_handler, codecov_vcr):
        assert await valid_handler.delete_comment("1", "113977323") is True

    @pytest.mark.asyncio
    async def test_delete_comment_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.delete_comment("1", 113977999)

    @pytest.mark.asyncio
    async def test_find_pull_request_nothing_found(self, valid_handler, codecov_vcr):
        # nothing matches commit or branch
        assert await valid_handler.find_pull_request("a" * 40, "no-branch") is None

    @pytest.mark.asyncio
    async def test_find_pull_request_pr_found(self, valid_handler, codecov_vcr):
        commitid = "dd798926730aad14aadf72281204bdb85734fe67"
        assert (
            await valid_handler.find_pull_request(commit=commitid, state="close") == 2
        )
        assert await valid_handler.find_pull_request(commit=commitid, state="open") == 1

    @pytest.mark.asyncio
    async def test_find_pull_request_pr_found_branch(self, valid_handler, codecov_vcr):
        branch = "other-branch"
        assert await valid_handler.find_pull_request(branch=branch, state="close") == 2
        assert await valid_handler.find_pull_request(branch=branch, state="open") == 1

    @pytest.mark.asyncio
    async def test_find_pull_request_merge_requests_disabled(
        self, valid_handler, codecov_vcr
    ):
        # merge requests turned off on Gitlab settings
        res = await valid_handler.find_pull_request("a" * 40)
        assert res is None

    @pytest.mark.asyncio
    async def test_find_pull_request_project_not_found(
        self, valid_handler, codecov_vcr
    ):
        with pytest.raises(TorngitClientError) as excinfo:
            await valid_handler.find_pull_request("a" * 40)
        assert excinfo.value.code == 404

    @pytest.mark.asyncio
    async def test_get_pull_request_fail(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_pull_request("100")

    get_pull_request_test_data = [
        (
            "1",
            {
                "base": {
                    "branch": "main",
                    "commitid": "5716de23b27020419d1a40dd93b469c041a1eeef",
                },
                "head": {
                    "branch": "other-branch",
                    "commitid": "dd798926730aad14aadf72281204bdb85734fe67",
                },
                "number": "1",
                "id": "1",
                "state": "merged",
                "title": "Other branch",
                "author": {"id": "109640", "username": "codecov"},
                "merge_commit_sha": "dd798926730aad14aadf72281204bdb85734fe67",
            },
        )
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("a,b", get_pull_request_test_data)
    async def test_get_pull_request(self, valid_handler, a, b, codecov_vcr):
        res = await valid_handler.get_pull_request(a)
        assert res == b

    @pytest.mark.asyncio
    async def test_get_pull_request_with_diff_refs(self, codecov_vcr):
        recent_handler = Gitlab(
            repo=dict(service_id="18347774", name="codecov-example"),
            owner=dict(username="ThiagoCodecov", service_id="_meaningless_"),
            token=dict(key=16 * "f882"),
        )
        res = await recent_handler.get_pull_request("1")
        assert res == {
            "author": {"id": "3124507", "username": "ThiagoCodecov"},
            "base": {
                "branch": "main",
                "commitid": "081d91921f05a8a39d39aef667eddb88e96300c7",
            },
            "head": {
                "branch": "thiago/base-no-base",
                "commitid": "b34b00d0872d129943b634693fd8f19f5f37acf9",
            },
            "state": "merged",
            "title": "Thiago/base no base",
            "id": "1",
            "number": "1",
            "merge_commit_sha": "b34b00d0872d129943b634693fd8f19f5f37acf9",
        }

    @pytest.mark.asyncio
    async def test_get_pull_request_files(self, codecov_vcr):
        recent_handler = Gitlab(
            repo=dict(service_id="30951850", name="learn-gitlab"),
            owner=dict(username="codecove2e", service_id="10119799"),
            token=dict(key=16 * "f882"),
        )
        res = await recent_handler.get_pull_request_files("1")

        assert res == [
            "README.md",
        ]

    @pytest.mark.asyncio
    async def test_get_pull_request_commits(self, valid_handler, codecov_vcr):
        expected_result = ["dd798926730aad14aadf72281204bdb85734fe67"]
        res = await valid_handler.get_pull_request_commits("1")
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_pull_requests(self, valid_handler, codecov_vcr):
        expected_result = [1]
        res = await valid_handler.get_pull_requests()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_commit(self, valid_handler, codecov_vcr):
        commit = await valid_handler.get_commit(
            "0028015f7fa260f5fd68f78c0deffc15183d955e"
        )
        assert commit == {
            "author": {
                "id": None,
                "username": None,
                "email": "steve@stevepeak.net",
                "name": "stevepeak",
            },
            "message": "added large file\n",
            "parents": ["5716de23b27020419d1a40dd93b469c041a1eeef"],
            "commitid": "0028015f7fa260f5fd68f78c0deffc15183d955e",
            "timestamp": "2014-10-19T14:32:33.000Z",
        }

    @pytest.mark.asyncio
    async def test_get_commit_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_commit("none")

    @pytest.mark.asyncio
    async def test_get_commit_diff_file_change(self, valid_handler, codecov_vcr):
        expected_result = {
            "files": {
                "large.md": {
                    "before": None,
                    "segments": [{"header": ["0", "0", "1", "816"]}],
                    "stats": {"added": 816, "removed": 0},
                    "type": "modified",
                }
            }
        }
        res = await valid_handler.get_commit_diff(
            "0028015f7fa260f5fd68f78c0deffc15183d955e"
        )
        assert "files" in res
        assert "large.md" in res["files"]
        assert "segments" in res["files"]["large.md"]
        assert len(res["files"]["large.md"]["segments"]) == 1
        assert "lines" in res["files"]["large.md"]["segments"][0]
        assert len(res["files"]["large.md"]["segments"][0].pop("lines")) == 816
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_commit_diff(self, valid_handler, codecov_vcr):
        expected_result = {
            "files": {
                "README.md": {
                    "before": None,
                    "segments": [
                        {
                            "header": ["1", "5", "1", "15"],
                            "lines": [
                                "-### Example",
                                "+### CI Testing",
                                " ",
                                "-> This repo is used for CI "
                                "Testing. Enjoy this gif as a "
                                "reward!",
                                "+> This repo is used for CI " "Testing",
                                "+",
                                "+",
                                "+| [https://codecov.io/][1] "
                                "| [@codecov][2] | "
                                "[hello@codecov.io][3] |",
                                "+| ------------------------ "
                                "| ------------- | "
                                "--------------------- |",
                                "+",
                                "+-----",
                                "+",
                                "+",
                                "+[1]: https://codecov.io/",
                                "+[2]: " "https://twitter.com/codecov",
                                "+[3]: " "mailto:hello@codecov.io",
                                " ",
                                "-![i can do " "that](http://gph.is/17cvPc4)",
                            ],
                        }
                    ],
                    "stats": {"added": 13, "removed": 3},
                    "type": "modified",
                }
            }
        }
        res = await valid_handler.get_commit_diff(
            "c739768fcac68144a3a6d82305b9c4106934d31a"
        )
        print(list(res.keys()))
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_commit_statuses(self, valid_handler, codecov_vcr):
        res = await valid_handler.get_commit_statuses(
            "c739768fcac68144a3a6d82305b9c4106934d31a"
        )
        assert res == "success"

    @pytest.mark.asyncio
    async def test_set_commit_status(self, valid_handler, codecov_vcr):
        target_url = "https://localhost:50036/gitlab/codecov/ci-repo?ref=ad798926730aad14aadf72281204bdb85734fe67"
        expected_result = {
            "allow_failure": False,
            "author": {
                "avatar_url": "https://secure.gravatar.com/avatar/dcdb35375db567705dd7e74226fae67b?s=80&d=identicon",
                "id": 109640,
                "name": "Codecov",
                "state": "active",
                "username": "codecov",
                "web_url": "https://gitlab.com/codecov",
            },
            "coverage": None,
            "description": "aaaaaaaaaa",
            "finished_at": "2018-11-05T20:11:18.137Z",
            "id": 116703167,
            "name": "context",
            "ref": "main",
            "sha": "c739768fcac68144a3a6d82305b9c4106934d31a",
            "started_at": None,
            "status": "success",
            "target_url": target_url,
            "created_at": "2018-11-05T20:11:18.104Z",
        }
        res = await valid_handler.set_commit_status(
            "c739768fcac68144a3a6d82305b9c4106934d31a",
            "success",
            "context",
            "aaaaaaaaaa",
            target_url,
        )
        assert res["author"] == expected_result["author"]
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_branches(self, valid_handler, codecov_vcr):
        branches = sorted(await valid_handler.get_branches())
        print(branches)
        assert list(map(lambda a: a[0], branches)) == ["main", "other-branch"]

    @pytest.mark.asyncio
    async def test_get_branch(self, valid_handler, codecov_vcr):
        expected_result = {
            "name": "main",
            "sha": "0fc784af11c401449e56b24a174bae7b9af86c98",
        }
        branch = await valid_handler.get_branch("main")
        print(branch)
        assert branch == expected_result

    @pytest.mark.asyncio
    async def test_post_webhook(self, valid_handler, codecov_vcr):
        url = "http://requestbin.net/r/1ecyaj51"
        name, events, secret = "a", {"job_events": True}, "d"
        expected_result = {
            "confidential_issues_events": False,
            "confidential_note_events": None,
            "created_at": "2018-11-06T04:51:57.164Z",
            "enable_ssl_verification": True,
            "id": 422507,
            "issues_events": False,
            "job_events": True,
            "merge_requests_events": False,
            "note_events": False,
            "pipeline_events": False,
            "project_id": 187725,
            "push_events": True,
            "push_events_branch_filter": None,
            "repository_update_events": False,
            "tag_push_events": False,
            "url": "http://requestbin.net/r/1ecyaj51",
            "wiki_page_events": False,
        }
        res = await valid_handler.post_webhook(name, url, events, secret)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_edit_webhook(self, valid_handler, codecov_vcr):
        url = "http://requestbin.net/r/1ecyaj51"
        events = {"tag_push_events": True, "note_events": True}
        new_name, secret = "new_name", "new_secret"
        expected_result = {
            "confidential_issues_events": False,
            "confidential_note_events": None,
            "created_at": "2018-11-06T04:51:57.164Z",
            "enable_ssl_verification": True,
            "id": 422507,
            "issues_events": False,
            "job_events": True,
            "merge_requests_events": False,
            "note_events": True,  # Notice this changed
            "pipeline_events": False,
            "project_id": 187725,
            "push_events": True,
            "push_events_branch_filter": None,
            "repository_update_events": False,
            "tag_push_events": True,  # Notice this changeds
            "url": "http://requestbin.net/r/1ecyaj51",
            "wiki_page_events": False,
        }
        res = await valid_handler.edit_webhook("422507", new_name, url, events, secret)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_delete_webhook(self, valid_handler, codecov_vcr):
        res = await valid_handler.delete_webhook("422507")
        assert res is True

    @pytest.mark.asyncio
    async def test_delete_webhook_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.delete_webhook("422507987")

    @pytest.mark.asyncio
    async def test_get_authenticated(self, valid_handler, codecov_vcr):
        res = await valid_handler.get_authenticated()
        assert res == (True, True)

    @pytest.mark.asyncio
    async def test_get_compare(self, valid_handler, codecov_vcr):
        base, head = "b33e1281", "5716de23"
        expected_result = {
            "diff": {
                "files": {
                    "README.md": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["1", "5", "1", "15"],
                                "lines": [
                                    "-### Example",
                                    "+### CI Testing",
                                    " ",
                                    "-> This repo is used for CI Testing. Enjoy this gif as a reward!",
                                    "+> This repo is used for CI Testing",
                                    "+",
                                    "+",
                                    "+| [https://codecov.io/][1] | [@codecov][2] | [hello@codecov.io][3] |",
                                    "+| ------------------------ | ------------- | --------------------- |",
                                    "+",
                                    "+-----",
                                    "+",
                                    "+",
                                    "+[1]: https://codecov.io/",
                                    "+[2]: https://twitter.com/codecov",
                                    "+[3]: mailto:hello@codecov.io",
                                    " ",
                                    "-![i can do that](http://gph.is/17cvPc4)",
                                ],
                            }
                        ],
                        "stats": {"added": 13, "removed": 3},
                    },
                    "folder/hello-world.txt": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {"header": ["0", "0", "1", ""], "lines": ["+hello world"]}
                        ],
                        "stats": {"added": 1, "removed": 0},
                    },
                }
            },
            "commits": [
                {
                    "commitid": "5716de23b27020419d1a40dd93b469c041a1eeef",
                    "message": "addd folder",
                    "timestamp": "2014-08-21T18:36:38.000Z",
                    "author": {"email": "steve@stevepeak.net", "name": "stevepeak"},
                },
                {
                    "commitid": "c739768fcac68144a3a6d82305b9c4106934d31a",
                    "message": "shhhh i'm batman!",
                    "timestamp": "2014-08-20T21:52:44.000Z",
                    "author": {"email": "steve@stevepeak.net", "name": "stevepeak"},
                },
            ],
        }
        res = await valid_handler.get_compare(base, head)
        print(res)
        assert sorted(list(res.keys())) == sorted(list(expected_result.keys()))
        for key in res:
            assert res[key] == expected_result[key]
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_repository(self, valid_handler, codecov_vcr):
        expected_result = {
            "owner": {"service_id": "109640", "username": "codecov"},
            "repo": {
                "branch": "main",
                "language": None,
                "name": "ci-repo",
                "private": False,
                "service_id": "187725",
            },
        }
        res = await valid_handler.get_repository()
        assert res["repo"] == expected_result["repo"]
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_repo_languages(self, valid_handler, codecov_vcr):
        expected_result = ["python"]
        res = await valid_handler.get_repo_languages()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_repository_subgroup(self, valid_handler, codecov_vcr):
        # test get_repository for repo in a subgroup
        expected_result = {
            "owner": {"service_id": "4165905", "username": "l00p_group_1:subgroup1"},
            "repo": {
                "branch": "main",
                "language": None,
                "name": "proj-a",
                "private": True,
                "service_id": "9715852",
            },
        }
        res = await Gitlab(
            repo=dict(service_id="9715852"),
            owner=dict(username="1nf1n1t3l00p"),
            token=dict(key=16 * "f882"),
        ).get_repository()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_repository_subgroup_no_repo_service_id(self, codecov_vcr):
        # test get repo in a subgroup when no repo service_id which happens when a user
        # tries to view a repo on legacy codecov.io and the repo is not in the database yet
        expected_result = {
            "owner": {"service_id": "4165905", "username": "l00p_group_1:subgroup1"},
            "repo": {
                "branch": "main",
                "language": None,
                "name": "proj-a",
                "private": True,
                "service_id": "9715852",
            },
        }
        res = await Gitlab(
            repo=dict(name="proj-a"),
            owner=dict(username="l00p_group_1:subgroup1"),
            token=dict(key=16 * "f882"),
        ).get_repository()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_master(self, valid_handler, codecov_vcr):
        expected_result = {
            "commitid": None,
            "content": b"import unittest\nimport my_package\n\n\nclass TestMethods(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(my_package.add(10), 20)\n\nif __name__ == '__main__':\n    unittest.main()\n",
        }
        path, ref = "tests.py", "master"
        res = await valid_handler.get_source(path, ref)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_random_commit(self, valid_handler, codecov_vcr):
        expected_result = {"commitid": None, "content": b"hello world\n"}
        path, ref = "folder/hello-world.txt", "5716de23"
        res = await valid_handler.get_source(path, ref)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_random_commit_not_found(self, valid_handler, codecov_vcr):
        path, ref = "awesome/non_exising_file.py", "5716de23"
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_source(path, ref)

    @pytest.mark.asyncio
    async def test_list_repos(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "owner": {"service_id": "189208", "username": "morerunes"},
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "delectamentum-mud-server",
                    "private": False,
                    "service_id": "1384844",
                },
            },
            {
                "owner": {"service_id": "109640", "username": "codecov"},
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "example-python",
                    "private": False,
                    "service_id": "580838",
                },
            },
            {
                "owner": {"service_id": "109640", "username": "codecov"},
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "ci-private",
                    "private": True,
                    "service_id": "190307",
                },
            },
            {
                "owner": {"service_id": "109640", "username": "codecov"},
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "ci-repo",
                    "private": False,
                    "service_id": "187725",
                },
            },
        ]
        res = await valid_handler.list_repos()
        assert res == expected_result

    @pytest.mark.asyncio
    @vcr.use_cassette(
        "tests/integration/cassetes/test_gitlab/TestGitlabTestCase/test_list_repos.yaml",
        record_mode="once",
        filter_headers=["authorization"],
        match_on=["method", "scheme", "host", "port", "path", "query"],
        filter_query_parameters=["oauth_nonce", "oauth_timestamp", "oauth_signature"],
    )
    async def test_list_repos_generator(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "owner": {"service_id": "189208", "username": "morerunes"},
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "delectamentum-mud-server",
                    "private": False,
                    "service_id": "1384844",
                },
            },
            {
                "owner": {"service_id": "109640", "username": "codecov"},
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "example-python",
                    "private": False,
                    "service_id": "580838",
                },
            },
            {
                "owner": {"service_id": "109640", "username": "codecov"},
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "ci-private",
                    "private": True,
                    "service_id": "190307",
                },
            },
            {
                "owner": {"service_id": "109640", "username": "codecov"},
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "ci-repo",
                    "private": False,
                    "service_id": "187725",
                },
            },
        ]
        repos = []
        page_count = 0
        async for page in valid_handler.list_repos_generator():
            repos.extend(page)
            page_count += 1
        assert page_count == 1
        assert repos == expected_result

    @pytest.mark.asyncio
    async def test_list_repos_subgroups(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "owner": {
                    "service_id": "4165907",
                    "username": "l00p_group_1:subgroup2",
                },
                "repo": {
                    "service_id": "9715886",
                    "name": "flake8",
                    "private": True,
                    "language": None,
                    "branch": "main",
                },
            },
            {
                "owner": {"service_id": "3215137", "username": "1nf1n1t3l00p"},
                "repo": {
                    "service_id": "9715862",
                    "name": "inf-proj",
                    "private": True,
                    "language": None,
                    "branch": "main",
                },
            },
            {
                "owner": {"service_id": "4165904", "username": "l00p_group_1"},
                "repo": {
                    "service_id": "9715859",
                    "name": "loop-proj",
                    "private": True,
                    "language": None,
                    "branch": "main",
                },
            },
            {
                "owner": {
                    "service_id": "4165905",
                    "username": "l00p_group_1:subgroup1",
                },
                "repo": {
                    "service_id": "9715852",
                    "name": "proj-a",
                    "private": True,
                    "language": None,
                    "branch": "main",
                },
            },
        ]
        res = await Gitlab(
            repo=dict(service_id="9715852"),
            owner=dict(username="1nf1n1t3l00p"),
            token=dict(key=16 * "f882"),
        ).list_repos()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_list_repos_subgroups_from_subgroups_username(
        self, valid_handler, codecov_vcr
    ):
        expected_result = [
            {
                "owner": {"service_id": "4037482", "username": "codecov-organization"},
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "demo-gitlab",
                    "private": True,
                    "service_id": "12060694",
                },
            },
            {
                "owner": {"service_id": "4037482", "username": "codecov-organization"},
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "codecov-assume-flag-test",
                    "private": True,
                    "service_id": "10575601",
                },
            },
            {
                "owner": {"service_id": "4037482", "username": "codecov-organization"},
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "migration-tests",
                    "private": True,
                    "service_id": "9422435",
                },
            },
            {
                "owner": {
                    "service_id": "5938764",
                    "username": "thiagocodecovtestgroup:test-subgroup",
                },
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "tasks",
                    "private": True,
                    "service_id": "14027433",
                },
            },
            {
                "owner": {
                    "service_id": "5938764",
                    "username": "thiagocodecovtestgroup:test-subgroup",
                },
                "repo": {
                    "branch": "main",
                    "language": None,
                    "name": "grouptestprojecttrr",
                    "private": True,
                    "service_id": "14026543",
                },
            },
        ]
        res = await Gitlab(
            repo=dict(service_id="5938764"),
            owner=dict(username="thiagocodecovtestgroup:test-subgroup"),
            token=dict(key=16 * "f882"),
        ).list_repos()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_list_teams(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "id": 726800,
                "name": "delectamentum-mud",
                "username": "delectamentum-mud",
                "avatar_url": None,
                "parent_id": None,
            }
        ]
        res = await valid_handler.list_teams()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_list_teams_subgroups(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "username": "l00p_group_1",
                "avatar_url": "https://assets.gitlab-static.net/uploads/-/system/user/avatar/4165904/avatar.png",
                "id": 4165904,
                "name": "My Awesome Group",
                "parent_id": None,
            },
            {
                "username": "l00p_group_1:subgroup1",
                "avatar_url": None,
                "id": 4165905,
                "name": "subgroup1",
                "parent_id": 4165904,
            },
            {
                "username": "l00p_group_1:subgroup2",
                "avatar_url": None,
                "id": 4165907,
                "name": "subgroup2",
                "parent_id": 4165904,
            },
        ]
        res = await Gitlab(
            repo=dict(service_id="9715852"),
            owner=dict(username="1nf1n1t3l00p"),
            token=dict(key=16 * "f882"),
        ).list_teams()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_list_top_level_files(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "id": "1da1ddbfe1ed846f7493964bf489754e464eef64",
                "mode": "040000",
                "name": "folder",
                "path": "folder",
                "type": "folder",
            },
            {
                "id": "c77cff04774d6debf9f8f645323fbe1cea368692",
                "mode": "100644",
                "name": ".gitignore",
                "path": ".gitignore",
                "type": "file",
            },
            {
                "id": "321cc67810818865affe8f6bac28f50d3c0a761c",
                "mode": "100644",
                "name": ".travis.yml",
                "path": ".travis.yml",
                "type": "file",
            },
            {
                "id": "7974a2260a70aab9ce8ae581fba307c6d448c468",
                "mode": "100644",
                "name": "README.md",
                "path": "README.md",
                "type": "file",
            },
            {
                "id": "c6b04a8c4a6bd3f8c12e65c7ad3ac759166298dd",
                "mode": "100644",
                "name": "large.md",
                "path": "large.md",
                "type": "file",
            },
            {
                "id": "478e1519b72ffd69712d77c5f50dd45b203846c4",
                "mode": "100644",
                "name": "my_package.py",
                "path": "my_package.py",
                "type": "file",
            },
            {
                "id": "20642e5c79ebd16b1c87ca300ff8b1afd478be5e",
                "mode": "100644",
                "name": "tests.py",
                "path": "tests.py",
                "type": "file",
            },
        ]

        res = await valid_handler.list_top_level_files("main")
        assert sorted(res, key=lambda x: x["path"]) == sorted(
            expected_result, key=lambda x: x["path"]
        )

    @pytest.mark.asyncio
    async def test_list_files(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "id": "3b18e512dba79e4c8300dd08aeb37f8e728b8dad",
                "name": "hello-world.txt",
                "type": "file",
                "path": "folder/hello-world.txt",
                "mode": "100644",
            }
        ]

        res = await valid_handler.list_files("main", "folder")
        assert sorted(res, key=lambda x: x["path"]) == sorted(
            expected_result, key=lambda x: x["path"]
        )

    @pytest.mark.asyncio
    async def test_get_ancestors_tree(self, valid_handler, codecov_vcr):
        commitid = "c739768fcac68144a3a6d82305b9c4106934d31a"
        res = await valid_handler.get_ancestors_tree(commitid)
        expected_result = {
            "commitid": "c739768fcac68144a3a6d82305b9c4106934d31a",
            "parents": [
                {
                    "commitid": "b33e12816cc3f386dae8add4968cedeff5155021",
                    "parents": [
                        {
                            "commitid": "743b04806ea677403aa2ff26c6bdeb85005de658",
                            "parents": [],
                        }
                    ],
                }
            ],
        }
        assert res == expected_result

    def test_get_href(self, valid_handler):
        expected_result = "https://gitlab.com/codecov/ci-repo/commit/743b04806ea677403aa2ff26c6bdeb85005de658"
        res = valid_handler.get_href(
            Endpoints.commit_detail, commitid="743b04806ea677403aa2ff26c6bdeb85005de658"
        )
        assert res == expected_result

    def test_get_href_subgroup(self, subgroup_handler):
        commitid = "743b04806ea677403aa2ff26c6bdeb85005de658"
        expected_result = f"https://gitlab.com/group/subgroup1/subgroup2/codecov-test/commit/{commitid}"
        res = subgroup_handler.get_href(Endpoints.commit_detail, commitid=commitid)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_make_paginated_call_no_limit(self, codecov_vcr):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_gitlab_total",
            labels={"endpoint": "list_teams"},
        )
        handler = Gitlab(
            repo=dict(service_id="9715852"),
            owner=dict(username="1nf1n1t3l00p"),
            token=dict(key=16 * "f882"),
        )
        url = handler.count_and_get_url_template("list_teams").substitute()
        res = handler.make_paginated_call(
            url, max_per_page=100, default_kwargs={}, counter_name="list_teams"
        )
        res = [i async for i in res]
        assert len(res) == 1
        assert list(len(p) for p in res) == [8]
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_gitlab_total",
            labels={"endpoint": "list_teams"},
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_make_paginated_call(self, codecov_vcr):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_gitlab_total",
            labels={"endpoint": "list_teams"},
        )
        handler = Gitlab(
            repo=dict(service_id="9715852"),
            owner=dict(username="1nf1n1t3l00p"),
            token=dict(key=16 * "f882"),
        )
        url = handler.count_and_get_url_template("list_teams").substitute()
        res = handler.make_paginated_call(
            url, max_per_page=4, default_kwargs={}, counter_name="list_teams"
        )
        res = [i async for i in res]
        assert len(res) == 3
        assert list(len(p) for p in res) == [4, 4, 1]
        assert codecov_vcr.play_count == 3
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_gitlab_total",
            labels={"endpoint": "list_teams"},
        )
        assert after - before == 3

    @pytest.mark.asyncio
    async def test_make_paginated_call_max_number_of_pages(self, codecov_vcr):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_gitlab_total",
            labels={"endpoint": "list_teams"},
        )
        handler = Gitlab(
            repo=dict(service_id="9715852"),
            owner=dict(username="1nf1n1t3l00p"),
            token=dict(key=16 * "f882"),
        )
        url = handler.count_and_get_url_template("list_teams").substitute()
        res = handler.make_paginated_call(
            url,
            max_per_page=3,
            max_number_of_pages=2,
            default_kwargs={},
            counter_name="list_teams",
        )
        res = [i async for i in res]
        assert len(res) == 2
        assert list(len(p) for p in res) == [3, 3]
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_gitlab_total",
            labels={"endpoint": "list_teams"},
        )
        assert after - before == 2

    @pytest.mark.asyncio
    async def test_get_authenticated_user(self, codecov_vcr):
        code = "7c005cbb342626fffe4f24e5eedac28d9e8fa1c8592808dd294bfe0d39ea084d"
        handler = Gitlab(oauth_consumer_token=dict(key=16 * "f882", secret=16 * "f882"))
        res = await handler.get_authenticated_user(
            code, "http://localhost:8000/login/gl"
        )
        assert res == {
            "id": 3124507,
            "name": "Thiago Ramos",
            "username": "ThiagoCodecov",
            "state": "active",
            "avatar_url": "https://secure.gravatar.com/avatar/337420e188ca8138d4b8599d3a20ad47?s=80&d=identicon",
            "web_url": "https://gitlab.com/ThiagoCodecov",
            "created_at": 1599149427,
            "bio": "",
            "bio_html": "",
            "location": None,
            "public_email": "",
            "skype": "",
            "linkedin": "",
            "twitter": "",
            "website_url": "",
            "organization": None,
            "job_title": "",
            "work_information": None,
            "last_sign_in_at": "2020-05-28T21:29:21.563Z",
            "confirmed_at": "2018-11-12T19:05:01.249Z",
            "last_activity_on": "2020-09-03",
            "email": "thiago@codecov.io",
            "theme_id": 1,
            "color_scheme_id": 1,
            "projects_limit": 100000,
            "current_sign_in_at": "2020-09-03T15:46:43.559Z",
            "identities": [
                {
                    "provider": "google_oauth2",
                    "extern_uid": "114705562456763720684",
                    "saml_provider_id": None,
                }
            ],
            "can_create_group": True,
            "can_create_project": True,
            "two_factor_enabled": False,
            "external": False,
            "private_profile": False,
            "shared_runners_minutes_limit": None,
            "extra_shared_runners_minutes_limit": None,
            "access_token": "testhi9nk25akajgzhudabirpz3vjau7qe8i9mavz2d9i1i0cfwjp8ggkcqavglx",
            "token_type": "Bearer",
            "refresh_token": "testwnoeg1a4bjhoa65vzxdn8grh4asp0b6l4idtdazw7ps5h8xx77m8gbyty7gi",
            "scope": "api",
        }

    @pytest.mark.asyncio
    async def test_is_student(self, valid_handler, codecov_vcr):
        res = await valid_handler.is_student()
        assert not res
