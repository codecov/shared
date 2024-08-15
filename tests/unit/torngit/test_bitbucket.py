from urllib.parse import parse_qsl, urlparse

import httpx
import pytest
import respx

from shared.torngit.bitbucket import Bitbucket
from shared.torngit.exceptions import (
    TorngitClientError,
    TorngitObjectNotFoundError,
    TorngitServer5xxCodeError,
    TorngitServerUnreachableError,
)


@pytest.fixture
def respx_vcr():
    with respx.mock as v:
        yield v


@pytest.fixture
def valid_handler():
    return Bitbucket(
        repo=dict(name="example-python"),
        owner=dict(
            username="ThiagoCodecov", service_id="6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49"
        ),
        oauth_consumer_token=dict(
            key="oauth_consumer_key_value", secret="oauth_consumer_token_secret_value"
        ),
        token=dict(secret="somesecret", key="somekey"),
    )


class TestUnitBitbucket(object):
    @pytest.mark.asyncio
    async def test_api_client_error_unreachable(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=599))
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitServerUnreachableError):
            await valid_handler.api(client, "2", method, url)

    @pytest.mark.asyncio
    async def test_api_client_error_connect_error(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(
                side_effect=httpx.ConnectError("message", request="request")
            )
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitServerUnreachableError):
            await valid_handler.api(client, "2", method, url)

    @pytest.mark.asyncio
    async def test_api_client_error_server_error(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=503))
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitServer5xxCodeError):
            await valid_handler.api(client, "2", method, url)

    @pytest.mark.asyncio
    async def test_api_client_error_client_error(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=404))
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitClientError):
            await valid_handler.api(client, "2", method, url)

    @pytest.mark.asyncio
    async def test_api_client_proper_params(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(
                return_value=mocker.MagicMock(text="kowabunga", status_code=200)
            )
        )
        method = "GET"
        url = "/random_url"
        res = await valid_handler.api(client, "2", method, url)
        assert res == "kowabunga"
        assert client.request.call_count == 1
        args, kwargs = client.request.call_args
        assert len(args) == 2
        assert args[0] == "GET"
        built_url = args[1]
        parsed_url = urlparse(built_url)
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc == "bitbucket.org"
        assert parsed_url.path == "/api/2.0/random_url"
        assert parsed_url.params == ""
        assert parsed_url.fragment == ""
        query = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
        assert sorted(query.keys()) == [
            "oauth_consumer_key",
            "oauth_nonce",
            "oauth_signature",
            "oauth_signature_method",
            "oauth_timestamp",
            "oauth_token",
            "oauth_version",
        ]
        assert (
            query["oauth_consumer_key"] == "oauth_consumer_key_value"
        )  # defined on `valid_handler`
        assert query["oauth_signature_method"] == "HMAC-SHA1"
        assert query["oauth_token"] == "somekey"  # defined on `valid_handler`
        assert query["oauth_version"] == "1.0"  # our class uses

    def test_generate_request_token(self, valid_handler):
        with respx.mock:
            my_route = respx.get(
                "https://bitbucket.org/api/1.0/oauth/request_token"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    content="oauth_token_secret=test7f35jt40fnbz5xanwn9tlsi5ci10&oauth_token=testh3xen5q215b9ex&oauth_callback_confirmed=true",
                )
            )
            v = valid_handler.generate_request_token("127.0.0.1/bb")
            assert v == {
                "oauth_token": "testh3xen5q215b9ex",
                "oauth_token_secret": "test7f35jt40fnbz5xanwn9tlsi5ci10",
            }
            assert my_route.call_count == 1

    def test_generate_access_token(self, valid_handler):
        with respx.mock:
            my_route = respx.get(
                "https://bitbucket.org/api/1.0/oauth/access_token"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    content="oauth_token_secret=test3j3wxslwkw2j27ncbntpcwq50kzh&oauth_token=testss3hxhcfqf1h6g",
                )
            )
            cookie_key, cookie_secret, oauth_verifier = (
                "rz5RKUeSbag6eeGrYj",
                "WG8RYGfhMggdj6aKVhHq4qtSUJq4paDX",
                "7403692316",
            )
            v = valid_handler.generate_access_token(
                cookie_key, cookie_secret, oauth_verifier
            )
            assert v == {
                "key": "testss3hxhcfqf1h6g",
                "secret": "test3j3wxslwkw2j27ncbntpcwq50kzh",
            }
            assert my_route.call_count == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "permission_name, expected_result",
        [("read", (True, False)), ("write", (True, True)), ("admin", (True, True))],
    )
    async def test_get_authenticated_private_200_status_some_permissions(
        self, mocker, respx_vcr, permission_name, expected_result
    ):
        respx.get(
            "https://bitbucket.org/api/2.0/repositories/ThiagoCodecov/example-python"
        ).respond(status_code=200, json={})
        respx.get(
            "https://bitbucket.org/api/2.0/user/permissions/repositories"
        ).respond(
            status_code=200,
            json={
                "pagelen": 10,
                "values": [
                    {
                        "type": "repository_permission",
                        "user": {
                            "display_name": "Thiago Ramos",
                            "uuid": "{9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645}",
                            "links": {},
                            "nickname": "thiago",
                            "type": "user",
                            "account_id": "5bce04c759d0e84f8c7555e9",
                        },
                        "repository": {
                            "links": {},
                            "type": "repository",
                            "name": "example-python",
                            "full_name": "ThiagoCodecov/example-python",
                            "uuid": "{a8c50527-2c3a-480e-afe1-7700e2b00074}",
                        },
                        "permission": permission_name,
                    }
                ],
                "page": 1,
            },
        )
        handler = Bitbucket(
            repo=dict(name="example-python", private=True),
            owner=dict(
                username="ThiagoCodecov",
                service_id="6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
            ),
            oauth_consumer_token=dict(
                key="oauth_consumer_key_value",
                secret="oauth_consumer_token_secret_value",
            ),
            token=dict(secret="somesecret", key="somekey"),
        )
        res = await handler.get_authenticated()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_authenticated_private_200_status_no_permission(
        self, mocker, respx_vcr
    ):
        respx.get(
            "https://bitbucket.org/api/2.0/repositories/ThiagoCodecov/example-python"
        ).respond(status_code=200, json={})
        respx.get(
            "https://bitbucket.org/api/2.0/user/permissions/repositories"
        ).respond(status_code=200, json={"pagelen": 10, "values": [], "page": 1})
        handler = Bitbucket(
            repo=dict(name="example-python", private=True),
            owner=dict(
                username="ThiagoCodecov",
                service_id="6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
            ),
            oauth_consumer_token=dict(
                key="oauth_consumer_key_value",
                secret="oauth_consumer_token_secret_value",
            ),
            token=dict(secret="somesecret", key="somekey"),
        )
        res = await handler.get_authenticated()
        assert res == (True, False)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "permission_name, expected_result",
        [("read", (True, False)), ("write", (True, True)), ("admin", (True, True))],
    )
    async def test_get_authenticated_private_404_status(
        self, mocker, respx_vcr, permission_name, expected_result
    ):
        respx.get(
            "https://bitbucket.org/api/2.0/repositories/ThiagoCodecov/example-python"
        ).respond(status_code=404, json={})
        handler = Bitbucket(
            repo=dict(name="example-python", private=True),
            owner=dict(
                username="ThiagoCodecov",
                service_id="6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
            ),
            oauth_consumer_token=dict(
                key="oauth_consumer_key_value",
                secret="oauth_consumer_token_secret_value",
            ),
            token=dict(secret="secret", key="key"),
        )
        with pytest.raises(TorngitClientError):
            await handler.get_authenticated()

    @pytest.mark.asyncio
    async def test_list_repos_exception_mid_call(self, valid_handler, respx_vcr):
        respx.get("https://bitbucket.org/api/2.0/user/permissions/workspaces").respond(
            status_code=200,
            json={
                "values": [
                    {
                        "workspace": {
                            "name": "banana",
                            "uuid": "[uuid]",
                            "slug": "specialslug",
                        }
                    },
                    {
                        "workspace": {
                            "name": "apple",
                            "uuid": "[abcdef]",
                            "slug": "anotherslug",
                        }
                    },
                ]
            },
        )
        respx.get(
            "https://bitbucket.org/api/2.0/user/permissions/repositories"
        ).respond(
            status_code=200,
            json={
                "values": [
                    {
                        "repository": {
                            "full_name": "codecov/worker",
                            "owner": {"username": "differentone"},
                        }
                    }
                ]
            },
        )
        respx.get("https://bitbucket.org/api/2.0/repositories/specialslug").respond(
            status_code=200, json={"values": []}
        )
        respx.get("https://bitbucket.org/api/2.0/repositories/ThiagoCodecov").respond(
            status_code=200, json={"values": []}
        )
        respx.get("https://bitbucket.org/api/2.0/repositories/anotherslug").respond(
            status_code=200,
            json={
                "values": [
                    {
                        "is_private": True,
                        "language": "python",
                        "uuid": "[haja]",
                        "full_name": "anotherslug/aaaa",
                        "owner": {"uuid": "[poilk]"},
                    },
                    {
                        "is_private": True,
                        "language": "python",
                        "uuid": "[haja]",
                        "full_name": "anotherslug/qwerty",
                        "owner": {"uuid": "[poilk]"},
                    },
                ]
            },
        )
        respx.get("https://bitbucket.org/api/2.0/repositories/codecov").respond(
            status_code=404, json={"values": []}
        )
        res = await valid_handler.list_repos()
        assert res == [
            {
                "owner": {"service_id": "poilk", "username": "anotherslug"},
                "repo": {
                    "service_id": "haja",
                    "name": "aaaa",
                    "language": "python",
                    "private": True,
                    "branch": "main",
                },
            },
            {
                "owner": {"service_id": "poilk", "username": "anotherslug"},
                "repo": {
                    "service_id": "haja",
                    "name": "qwerty",
                    "language": "python",
                    "private": True,
                    "branch": "main",
                },
            },
        ]

    @pytest.mark.asyncio
    async def test_get_compare(self, valid_handler, respx_vcr):
        diff = "\n".join(
            [
                "diff --git a/README.md b/README.md",
                "index 87f9baa..51c8a2d 100644",
                "--- a/README.md",
                "+++ b/README.md",
                "@@ -14,4 +14,2 @@ Truces luctuque cognovit, cum lanam ordine vereri relinquunt sit munere quidam.",
                " Solent **torvi clamare successit** ille memores rogum; serpens egi caelo,",
                "-moventem gelido volucrum reddidit fatalia, *in*. Abdit instant et, et hostis",
                "-amores, nec pater formosus mortis capiat eripui: ferarum extemplo. Inmeritas",
                " favilla qui Dauno portis Aello! Fluit inde magis vinci hastam amore, mihi fama",
            ]
        )
        base, head = "6ae5f17", "b92edba"
        respx.get(
            "https://bitbucket.org/api/2.0/repositories/ThiagoCodecov/example-python/diff/b92edba..6ae5f17",
            params__contains={"context": "1"},
        ).respond(status_code=200, content=diff, headers={"Content-Type": "aaaa"})
        expected_result = {
            "diff": {
                "files": {
                    "README.md": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["14", "4", "14", "2"],
                                "lines": [
                                    " Solent **torvi clamare successit** ille memores rogum; serpens egi caelo,",
                                    "-moventem gelido volucrum reddidit fatalia, *in*. Abdit instant et, et hostis",
                                    "-amores, nec pater formosus mortis capiat eripui: ferarum extemplo. Inmeritas",
                                    " favilla qui Dauno portis Aello! Fluit inde magis vinci hastam amore, mihi fama",
                                ],
                            }
                        ],
                        "stats": {"added": 0, "removed": 2},
                    }
                }
            },
            "commits": [{"commitid": "b92edba"}, {"commitid": "6ae5f17"}],
        }
        res = await valid_handler.get_compare(base, head)
        assert sorted(list(res.keys())) == sorted(list(expected_result.keys()))
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_distance_in_commits(self):
        expected_result = {
            "behind_by": None,
            "behind_by_commit": None,
            "status": None,
            "ahead_by": None,
        }
        handler = Bitbucket(
            repo=dict(name="example-python", private=True),
        )
        res = await handler.get_distance_in_commits("branch", "commit")
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_repo_languages(self):
        expected_result = ["javascript"]
        handler = Bitbucket(
            repo=dict(name="example-python", private=True),
        )
        res = await handler.get_repo_languages(None, "JavaScript")
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_repo_no_languages(self):
        expected_result = []
        handler = Bitbucket(
            repo=dict(name="example-python", private=True),
        )
        res = await handler.get_repo_languages(None, None)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_pull_rquest_files(self, valid_handler):
        handler = Bitbucket(
            repo=dict(name="test-repo"),
            owner=dict(username="e2e-org"),
            token=dict(secret="somesecret", key="somekey"),
            oauth_consumer_token=dict(
                key="oauth_consumer_key_value",
                secret="oauth_consumer_token_secret_value",
            ),
        )
        with respx.mock:
            respx.get(
                "https://bitbucket.org/api/2.0/repositories/e2e-org/test-repo/pullrequests/1/diffstat"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    json={
                        "values": [
                            {
                                "type": "diffstat",
                                "lines_added": 1,
                                "lines_removed": 1,
                                "status": "modified",
                                "old": {
                                    "path": "README.md",
                                    "type": "commit_file",
                                    "escaped_path": "README.md",
                                    "links": {
                                        "self": {
                                            "href": "https://bitbucket.org/!api/2.0/repositories/e2e-org/test-repo/src/d32434b65381acce9709e11234c0ba5ce2a9f515/README.md"
                                        }
                                    },
                                },
                                "new": {
                                    "path": "README.md",
                                    "type": "commit_file",
                                    "escaped_path": "README.md",
                                    "links": {
                                        "self": {
                                            "href": "https://bitbucket.org/!api/2.0/repositories/e2e-org/test-repo/src/8ed929e26c3e9dd51bb7abefc89f4f5044ff28fe/README.md"
                                        }
                                    },
                                },
                            }
                        ],
                        "pagelen": 500,
                        "size": 1,
                        "page": 1,
                    },
                )
            )
            v = await handler.get_pull_request_files("1")
            assert v == [
                "README.md",
            ]

    @pytest.mark.asyncio
    async def test_get_pull_request_files_404(self):
        handler = Bitbucket(
            repo=dict(name="test-repo"),
            owner=dict(username="e2e-org"),
            token=dict(secret="somesecret", key="somekey"),
            oauth_consumer_token=dict(
                key="oauth_consumer_key_value",
                secret="oauth_consumer_token_secret_value",
            ),
        )
        with respx.mock:
            respx.get(
                "https://bitbucket.org/api/2.0/repositories/e2e-org/test-repo/pullrequests/4/diffstat"
            ).mock(
                return_value=httpx.Response(
                    status_code=404,
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "1350085394",
                    },
                )
            )
            with pytest.raises(TorngitObjectNotFoundError) as excinfo:
                await handler.get_pull_request_files(4)
            assert excinfo.value.code == 404
            assert excinfo.value.message == "PR with id 4 does not exist"

    @pytest.mark.asyncio
    async def test_get_pull_request_files_403(self):
        handler = Bitbucket(
            repo=dict(name="test-repo"),
            owner=dict(username="e2e-org"),
            token=dict(secret="somesecret", key="somekey"),
            oauth_consumer_token=dict(
                key="oauth_consumer_key_value",
                secret="oauth_consumer_token_secret_value",
            ),
        )
        with respx.mock:
            respx.get(
                "https://bitbucket.org/api/2.0/repositories/e2e-org/test-repo/pullrequests/4/diffstat"
            ).mock(
                return_value=httpx.Response(
                    status_code=403,
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "1350085394",
                    },
                )
            )
            with pytest.raises(TorngitClientError) as excinfo:
                await handler.get_pull_request_files(4)
            assert excinfo.value.code == 403
            assert excinfo.value.message == "Bitbucket API: Forbidden"
