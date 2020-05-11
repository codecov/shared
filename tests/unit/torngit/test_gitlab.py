import socket

import pytest

from shared.torngit.gitlab import Gitlab
from shared.torngit.exceptions import TorngitServerUnreachableError


@pytest.fixture
def valid_handler():
    return Gitlab(
        repo=dict(name="example-python"),
        owner=dict(username="ThiagoCodecov"),
        token=dict(key="some_key"),
    )


class TestUnitGitlab(object):
    @pytest.mark.asyncio
    async def test_socker_gaierror(self, mocker, valid_handler):
        mocker.patch.object(Gitlab, "fetch", side_effect=socket.gaierror)
        with pytest.raises(TorngitServerUnreachableError):
            await valid_handler.api("get", "url")
