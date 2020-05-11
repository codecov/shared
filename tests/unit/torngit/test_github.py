import socket

import pytest

from shared.torngit.github import Github
from shared.torngit.exceptions import TorngitServerUnreachableError


@pytest.fixture
def valid_handler():
    return Github(
        repo=dict(name="example-python"),
        owner=dict(username="ThiagoCodecov"),
        token=dict(key="some_key"),
    )


class TestUnitGithub(object):
    @pytest.mark.asyncio
    async def test_socker_gaierror(self, mocker, valid_handler):
        mocker.patch.object(Github, "fetch", side_effect=socket.gaierror)
        with pytest.raises(TorngitServerUnreachableError):
            await valid_handler.api(
                "get", "/repos/%s/branches" % valid_handler.slug, per_page=100,
            )
