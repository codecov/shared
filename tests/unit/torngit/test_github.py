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

    def test_loggable_token(self, mocker, valid_handler):
        no_username_handler = Github(
            repo=dict(name="example-python"),
            owner=dict(username="ThiagoCodecov"),
            token=dict(key="some_key"),
        )
        assert no_username_handler.loggable_token == "f7CMr"
        with_username_handler = Github(
            repo=dict(name="example-python"),
            owner=dict(username="ThiagoCodecov"),
            token=dict(key="some_key", username="Thiago"),
        )
        assert with_username_handler.loggable_token == "Thiago's token"
        no_token_handler = Github(
            repo=dict(name="example-python"),
            owner=dict(username="ThiagoCodecov"),
            token=dict(key=None),
        )
        assert no_token_handler.loggable_token == "notoken"
