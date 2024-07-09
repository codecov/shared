from asyncio import Future
from unittest.mock import Mock, patch

import pytest

from shared.config import ConfigHelper, MissingConfigException
from shared.torngit.bitbucket_server import BitbucketServer, _Signature

# NOT A REAL KEY; this was generated for use in tests
mock_private_key = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDCFqq2ygFh9UQU/6PoDJ6L9e4ovLPCHtlBt7vzDwyfwr3XGxln
0VbfycVLc6unJDVEGZ/PsFEuS9j1QmBTTEgvCLR6RGpfzmVuMO8wGVEO52pH73h9
rviojaheX/u3ZqaA0di9RKy8e3L+T0ka3QYgDx5wiOIUu1wGXCs6PhrtEwICBAEC
gYBu9jsi0eVROozSz5dmcZxUAzv7USiUcYrxX007SUpm0zzUY+kPpWLeWWEPaddF
VONCp//0XU8hNhoh0gedw7ZgUTG6jYVOdGlaV95LhgY6yXaQGoKSQNNTY+ZZVT61
zvHOlPynt3GZcaRJOlgf+3hBF5MCRoWKf+lDA5KiWkqOYQJBAMQp0HNVeTqz+E0O
6E0neqQDQb95thFmmCI7Kgg4PvkS5mz7iAbZa5pab3VuyfmvnVvYLWejOwuYSp0U
9N8QvUsCQQD9StWHaVNM4Lf5zJnB1+lJPTXQsmsuzWvF3HmBkMHYWdy84N/TdCZX
Cxve1LR37lM/Vijer0K77wAx2RAN/ppZAkB8+GwSh5+mxZKydyPaPN29p6nC6aLx
3DV2dpzmhD0ZDwmuk8GN+qc0YRNOzzJ/2UbHH9L/lvGqui8I6WLOi8nDAkEA9CYq
ewfdZ9LcytGz7QwPEeWVhvpm0HQV9moetFWVolYecqBP4QzNyokVnpeUOqhIQAwe
Z0FJEQ9VWsG+Df0noQJBALFjUUZEtv4x31gMlV24oiSWHxIRX4fEND/6LpjleDZ5
C/tY+lZIEO1Gg/FxSMB+hwwhwfSuE3WohZfEcSy+R48=
-----END RSA PRIVATE KEY-----"""


def valid_handler():
    return BitbucketServer(
        repo=dict(name="python-standard"),
        owner=dict(username="TEST"),
        oauth_consumer_token=dict(key=""),
        token=dict(secret="", key=""),
    )


def mock_config_get(configs, mocker):
    orig_get = ConfigHelper.get

    def mock_get(obj, *args, **kwargs):
        conf_key = ".".join(args)
        if conf_key in configs:
            return configs.get(conf_key)
        else:
            return orig_get(obj, *args, **kwargs)

    m = mocker.patch.object(ConfigHelper, "get", mock_get)
    return m


def mock_config_load_file(configs, mocker):
    orig_load_file = ConfigHelper.load_filename_from_path

    def mock_load_file(obj, *args):
        conf_key = ".".join(args)
        if conf_key in configs:
            return configs.get(conf_key)
        else:
            return orig_load_file(obj, *args)

    m = mocker.patch.object(ConfigHelper, "load_filename_from_path", mock_load_file)
    return m


class TestBitbucketTestCase(object):
    def test_signature_without_config(self, mocker):
        _Signature.privkey = None

        def raise_missing_config(obj, *args, **kwargs):
            raise MissingConfigException(args)

        mocker.patch.object(ConfigHelper, "get", side_effect=raise_missing_config)

        signature = _Signature()

        mock_req = Mock(
            method="get", normalized_url="", get_normalized_parameters=lambda: ""
        )
        mock_token = Mock(secret="")
        mock_consumer = Mock(secret="")

        try:
            signature.sign(mock_req, mock_consumer, mock_token)
        except MissingConfigException:
            assert True
        else:
            assert False, "MissingConfigException should have been thrown"

    def test_signature_with_invalid_config(self, mocker):
        _Signature.privkey = None
        mock_config_get({"bitbucket_server.pemfile": "/invalid"}, mocker)

        signature = _Signature()
        mock_req = Mock(
            method="get", normalized_url="", get_normalized_parameters=lambda: ""
        )
        mock_token = Mock(secret="")
        mock_consumer = Mock(secret="")

        try:
            signature.sign(mock_req, mock_consumer, mock_token)
        except FileNotFoundError:
            assert True
        else:
            assert False, "FileNotFoundError should have been thrown"

    def test_signature_with_invalid_pemfile(self, mocker):
        _Signature.privkey = None
        mock_config_load_file({"bitbucket_server.pemfile": "invalid pemfile"}, mocker)

        signature = _Signature()
        mock_req = Mock(
            method="get", normalized_url="", get_normalized_parameters=lambda: ""
        )
        mock_token = Mock(secret="")
        mock_consumer = Mock(secret="")

        try:
            signature.sign(mock_req, mock_consumer, mock_token)
        except SyntaxError:
            assert True
        else:
            assert False, "SyntaxError should have been thrown"

    def test_signature_with_valid_pemfile(self, mocker):
        _Signature.privkey = None

        mock_config_load_file({"bitbucket_server.pemfile": mock_private_key}, mocker)

        signature = _Signature()
        mock_req = Mock(
            method="get", normalized_url="", get_normalized_parameters=lambda: ""
        )
        mock_token = Mock(secret="")
        mock_consumer = Mock(secret="")

        try:
            signature.sign(mock_req, mock_consumer, mock_token)
        except Exception:
            assert False, "This operation should have succeeded"
        else:
            assert True

    """
    def test_signature_without_pemfile(self, mocker):
        mock_config_factory({"bitbucket_server.pemfile": None}, mocker)

        self.assertRaises(



        signature = _Signature()
        handler = valid_handler()
    """

    @pytest.mark.asyncio
    async def test_find_pull_request_found(self, mocker):
        api_result = {
            "size": 1,
            "limit": 25,
            "isLastPage": True,
            "values": [
                {
                    "id": 3,
                    "version": 9,
                    "title": "brand-new-branch-1591913005",
                    "state": "OPEN",
                    "open": True,
                    "closed": False,
                    "createdDate": 1591913044441,
                    "updatedDate": 1591913541017,
                    "fromRef": {
                        "id": "refs/heads/brand-new-branch",
                        "displayId": "brand-new-branch",
                        "latestCommit": "86be80adfc64355e523c38ef9b9bab7408c173e3",
                        "repository": {
                            "slug": "python-standard",
                            "id": 1,
                            "name": "python-standard",
                            "hierarchyId": "0199083afd9cd1cffafe",
                            "scmId": "git",
                            "state": "AVAILABLE",
                            "statusMessage": "Available",
                            "forkable": False,
                            "project": {
                                "key": "TEST",
                                "id": 1,
                                "name": "Test",
                                "public": False,
                                "type": "NORMAL",
                                "links": {
                                    "self": [
                                        {
                                            "href": "https://bitbucket-server.codecov.dev:8443/projects/TEST"
                                        }
                                    ]
                                },
                            },
                            "public": False,
                            "links": {
                                "clone": [
                                    {
                                        "href": "ssh://git@bitbucket-server.codecov.dev:7999/test/python-standard.git",
                                        "name": "ssh",
                                    },
                                    {
                                        "href": "https://bitbucket-server.codecov.dev:8443/scm/test/python-standard.git",
                                        "name": "http",
                                    },
                                ],
                                "self": [
                                    {
                                        "href": "https://bitbucket-server.codecov.dev:8443/projects/TEST/repos/python-standard/browse"
                                    }
                                ],
                            },
                        },
                    },
                    "toRef": {
                        "id": "refs/heads/master",
                        "displayId": "master",
                        "latestCommit": "f3d4a16b651356d9599bd634f6be868508f81f99",
                        "repository": {
                            "slug": "python-standard",
                            "id": 1,
                            "name": "python-standard",
                            "hierarchyId": "0199083afd9cd1cffafe",
                            "scmId": "git",
                            "state": "AVAILABLE",
                            "statusMessage": "Available",
                            "forkable": False,
                            "project": {
                                "key": "TEST",
                                "id": 1,
                                "name": "Test",
                                "public": False,
                                "type": "NORMAL",
                                "links": {
                                    "self": [
                                        {
                                            "href": "https://bitbucket-server.codecov.dev:8443/projects/TEST"
                                        }
                                    ]
                                },
                            },
                            "public": False,
                            "links": {
                                "clone": [
                                    {
                                        "href": "ssh://git@bitbucket-server.codecov.dev:7999/test/python-standard.git",
                                        "name": "ssh",
                                    },
                                    {
                                        "href": "https://bitbucket-server.codecov.dev:8443/scm/test/python-standard.git",
                                        "name": "http",
                                    },
                                ],
                                "self": [
                                    {
                                        "href": "https://bitbucket-server.codecov.dev:8443/projects/TEST/repos/python-standard/browse"
                                    }
                                ],
                            },
                        },
                    },
                    "locked": False,
                    "author": {
                        "user": {
                            "name": "bbsadmin",
                            "emailAddress": "edward@codecov.io",
                            "id": 1,
                            "displayName": "BBS Admin",
                            "active": True,
                            "slug": "bbsadmin",
                            "type": "NORMAL",
                            "links": {
                                "self": [
                                    {
                                        "href": "https://bitbucket-server.codecov.dev:8443/users/bbsadmin"
                                    }
                                ]
                            },
                        },
                        "role": "AUTHOR",
                        "approved": False,
                        "status": "UNAPPROVED",
                    },
                    "reviewers": [],
                    "participants": [],
                    "links": {
                        "self": [
                            {
                                "href": "https://bitbucket-server.codecov.dev:8443/projects/TEST/repos/python-standard/pull-requests/3"
                            }
                        ]
                    },
                }
            ],
            "start": 0,
        }
        mocker.patch.object(BitbucketServer, "api", return_value=api_result)
        res = await valid_handler().find_pull_request(
            "86be80adfc64355e523c38ef9b9bab7408c173e3", "brand-new-branch"
        )
        assert res == 3

    @pytest.mark.asyncio
    async def test_find_pull_request_nothing_found(self, mocker):
        api_result = {
            "size": 0,
            "limit": 25,
            "isLastPage": True,
            "values": [],
            "start": 0,
        }
        mocker.patch.object(BitbucketServer, "api", return_value=api_result)
        assert await valid_handler().find_pull_request("a" * 40, "no-branch") is None

    @pytest.mark.asyncio
    async def test_list_top_level_files(self, mocker):
        api_result = {
            "values": [
                ".gitignore",
                ".travis.yml",
                "Dockerfile",
                "README.md",
                "codecov.yml",
                "coverage.xml",
                "docker-compose.yml",
                "entrypoint.sh",
                "src/index.py",
                "src/request.py",
                "src/test_index.py",
            ],
            "size": 11,
            "isLastPage": True,
            "start": 0,
            "limit": 25,
            "nextPageStart": None,
        }
        mocker.patch.object(BitbucketServer, "api", return_value=api_result)
        files = await valid_handler().list_top_level_files("ref", "")
        assert len(files) == 11

    @pytest.mark.asyncio
    async def test_diff_to_json(self, mocker):
        diff = [
            {
                "source": None,
                "destination": {
                    "components": [
                        "src",
                        "__pycache__",
                        "test_index.cpython-36-PYTEST.pyc",
                    ],
                    "parent": "src/__pycache__",
                    "name": "test_index.cpython-36-PYTEST.pyc",
                    "extension": "pyc",
                    "toString": "src/__pycache__/test_index.cpython-36-PYTEST.pyc",
                },
                "binary": True,
            },
            {
                "source": {
                    "components": ["src", "index.py"],
                    "parent": "src",
                    "name": "index.py",
                    "extension": "py",
                    "toString": "src/index.py",
                },
                "destination": {
                    "components": ["src", "index.py"],
                    "parent": "src",
                    "name": "index.py",
                    "extension": "py",
                    "toString": "src/index.py",
                },
                "hunks": [
                    {
                        "sourceLine": 1,
                        "sourceSpan": 10,
                        "destinationLine": 1,
                        "destinationSpan": 11,
                        "segments": [
                            {
                                "type": "ADDED",
                                "lines": [
                                    {
                                        "source": 1,
                                        "destination": 1,
                                        "line": "import asyncio",
                                        "truncated": False,
                                    }
                                ],
                                "truncated": False,
                            },
                            {
                                "type": "CONTEXT",
                                "lines": [
                                    {
                                        "source": 1,
                                        "destination": 2,
                                        "line": "def uncovered_if(var=True):",
                                        "truncated": False,
                                    },
                                    {
                                        "source": 2,
                                        "destination": 3,
                                        "line": "    if var:",
                                        "truncated": False,
                                    },
                                    {
                                        "source": 3,
                                        "destination": 4,
                                        "line": "      return False",
                                        "truncated": False,
                                    },
                                    {
                                        "source": 4,
                                        "destination": 5,
                                        "line": "    else:",
                                        "truncated": False,
                                    },
                                    {
                                        "source": 5,
                                        "destination": 6,
                                        "line": "      return True",
                                        "truncated": False,
                                    },
                                    {
                                        "source": 6,
                                        "destination": 7,
                                        "line": "",
                                        "truncated": False,
                                    },
                                    {
                                        "source": 7,
                                        "destination": 8,
                                        "line": "def fully_covered():",
                                        "truncated": False,
                                    },
                                    {
                                        "source": 8,
                                        "destination": 9,
                                        "line": "    return True;",
                                        "truncated": False,
                                    },
                                    {
                                        "source": 9,
                                        "destination": 10,
                                        "line": "",
                                        "truncated": False,
                                    },
                                    {
                                        "source": 10,
                                        "destination": 11,
                                        "line": "def uncovered():",
                                        "truncated": False,
                                    },
                                ],
                                "truncated": False,
                            },
                        ],
                        "truncated": False,
                    }
                ],
                "truncated": False,
            },
        ]
        assert valid_handler().diff_to_json(diff) is not None
