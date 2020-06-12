import pytest
import json

from unittest.mock import patch, Mock
from tornado.httpclient import HTTPError

from shared.torngit.enums import Endpoints
from shared.torngit.exceptions import (
    TorngitObjectNotFoundError,
    TorngitServerUnreachableError,
    TorngitServer5xxCodeError,
    TorngitClientError,
)

from asyncio import Future
from shared.torngit.bitbucket_server import BitbucketServer


def valid_handler():
    return BitbucketServer(
        repo=dict(name="python-standard"),
        owner=dict(username="TEST"),
        oauth_consumer_token=dict(key=""),
        token=dict(secret="", key=""),
    )


class TestBitbucketTestCase(object):
    @pytest.mark.asyncio
    async def test_find_pull_request_found(self, mocker):
        api_result = {"size":1,"limit":25,"isLastPage":True,"values":[{"id":3,"version":9,"title":"brand-new-branch-1591913005","state":"OPEN","open":True,"closed":False,"createdDate":1591913044441,"updatedDate":1591913541017,"fromRef":{"id":"refs/heads/brand-new-branch","displayId":"brand-new-branch","latestCommit":"86be80adfc64355e523c38ef9b9bab7408c173e3","repository":{"slug":"python-standard","id":1,"name":"python-standard","hierarchyId":"0199083afd9cd1cffafe","scmId":"git","state":"AVAILABLE","statusMessage":"Available","forkable":False,"project":{"key":"TEST","id":1,"name":"Test","public":False,"type":"NORMAL","links":{"self":[{"href":"https://bitbucket-server.codecov.dev:8443/projects/TEST"}]}},"public":False,"links":{"clone":[{"href":"ssh://git@bitbucket-server.codecov.dev:7999/test/python-standard.git","name":"ssh"},{"href":"https://bitbucket-server.codecov.dev:8443/scm/test/python-standard.git","name":"http"}],"self":[{"href":"https://bitbucket-server.codecov.dev:8443/projects/TEST/repos/python-standard/browse"}]}}},"toRef":{"id":"refs/heads/master","displayId":"master","latestCommit":"f3d4a16b651356d9599bd634f6be868508f81f99","repository":{"slug":"python-standard","id":1,"name":"python-standard","hierarchyId":"0199083afd9cd1cffafe","scmId":"git","state":"AVAILABLE","statusMessage":"Available","forkable":False,"project":{"key":"TEST","id":1,"name":"Test","public":False,"type":"NORMAL","links":{"self":[{"href":"https://bitbucket-server.codecov.dev:8443/projects/TEST"}]}},"public":False,"links":{"clone":[{"href":"ssh://git@bitbucket-server.codecov.dev:7999/test/python-standard.git","name":"ssh"},{"href":"https://bitbucket-server.codecov.dev:8443/scm/test/python-standard.git","name":"http"}],"self":[{"href":"https://bitbucket-server.codecov.dev:8443/projects/TEST/repos/python-standard/browse"}]}}},"locked":False,"author":{"user":{"name":"bbsadmin","emailAddress":"edward@codecov.io","id":1,"displayName":"BBS Admin","active":True,"slug":"bbsadmin","type":"NORMAL","links":{"self":[{"href":"https://bitbucket-server.codecov.dev:8443/users/bbsadmin"}]}},"role":"AUTHOR","approved":False,"status":"UNAPPROVED"},"reviewers":[],"participants":[],"links":{"self":[{"href":"https://bitbucket-server.codecov.dev:8443/projects/TEST/repos/python-standard/pull-requests/3"}]}},{"id":2,"version":16,"title":"Subz/test bb","description":"* New commit\r\n* New commit","state":"OPEN","open":True,"closed":False,"createdDate":1591911067379,"updatedDate":1591911556417,"fromRef":{"id":"refs/heads/subz/test-bb","displayId":"subz/test-bb","latestCommit":"a2df4cfe9db99130d48a93404e618a7213a93f55","repository":{"slug":"python-standard","id":1,"name":"python-standard","hierarchyId":"0199083afd9cd1cffafe","scmId":"git","state":"AVAILABLE","statusMessage":"Available","forkable":False,"project":{"key":"TEST","id":1,"name":"Test","public":False,"type":"NORMAL","links":{"self":[{"href":"https://bitbucket-server.codecov.dev:8443/projects/TEST"}]}},"public":False,"links":{"clone":[{"href":"ssh://git@bitbucket-server.codecov.dev:7999/test/python-standard.git","name":"ssh"},{"href":"https://bitbucket-server.codecov.dev:8443/scm/test/python-standard.git","name":"http"}],"self":[{"href":"https://bitbucket-server.codecov.dev:8443/projects/TEST/repos/python-standard/browse"}]}}},"toRef":{"id":"refs/heads/master","displayId":"master","latestCommit":"f3d4a16b651356d9599bd634f6be868508f81f99","repository":{"slug":"python-standard","id":1,"name":"python-standard","hierarchyId":"0199083afd9cd1cffafe","scmId":"git","state":"AVAILABLE","statusMessage":"Available","forkable":False,"project":{"key":"TEST","id":1,"name":"Test","public":False,"type":"NORMAL","links":{"self":[{"href":"https://bitbucket-server.codecov.dev:8443/projects/TEST"}]}},"public":False,"links":{"clone":[{"href":"ssh://git@bitbucket-server.codecov.dev:7999/test/python-standard.git","name":"ssh"},{"href":"https://bitbucket-server.codecov.dev:8443/scm/test/python-standard.git","name":"http"}],"self":[{"href":"https://bitbucket-server.codecov.dev:8443/projects/TEST/repos/python-standard/browse"}]}}},"locked":False,"author":{"user":{"name":"subhi","emailAddress":"subhi@codecov.io","id":52,"displayName":"Subhi","active":True,"slug":"subhi","type":"NORMAL","links":{"self":[{"href":"https://bitbucket-server.codecov.dev:8443/users/subhi"}]}},"role":"AUTHOR","approved":False,"status":"UNAPPROVED"},"reviewers":[],"participants":[],"links":{"self":[{"href":"https://bitbucket-server.codecov.dev:8443/projects/TEST/repos/python-standard/pull-requests/2"}]}}],"start":0}
        mocked_fetch = mocker.patch.object(
            BitbucketServer, "api", return_value=Future()
        )
        mocked_fetch.return_value.set_result(api_result)
        res = await valid_handler().find_pull_request("86be80adfc64355e523c38ef9b9bab7408c173e3", "brand-new-branch")
        assert res == 3

    @pytest.mark.asyncio
    async def test_find_pull_request_nothing_found(self, mocker):

        api_result = {"size":0,"limit":25,"isLastPage":True,"values":[],"start":0}
        mocked_fetch = mocker.patch.object(
            BitbucketServer, "api", return_value=Future()
        )
        mocked_fetch.return_value.set_result(api_result)
        assert await valid_handler().find_pull_request("a" * 40, "no-branch") is None
