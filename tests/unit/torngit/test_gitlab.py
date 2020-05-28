import socket
import pytest
from asyncio import Future
from json import dumps

from shared.torngit.gitlab import Gitlab
from shared.torngit.exceptions import TorngitServerUnreachableError


@pytest.fixture
def valid_handler():
    return Gitlab(
        repo=dict(service_id="187725", name="codecov-test"),
        owner=dict(username="ThiagoCodecov", service_id="109479"),
        token=dict(key="some_key"),
    )


class TestUnitGitlab(object):
    @pytest.mark.asyncio
    async def test_socker_gaierror(self, mocker, valid_handler):
        mocker.patch.object(Gitlab, "fetch", side_effect=socket.gaierror)
        with pytest.raises(TorngitServerUnreachableError):
            await valid_handler.api("get", "url")

    @pytest.mark.asyncio
    async def test_get_commit_statuses(self, mocker, valid_handler):
        mocked_fetch = mocker.patch.object(Gitlab, "fetch", return_value=Future())
        mocked_fetch.return_value.set_result(
            mocker.MagicMock(
                headers={"Content-Type": "application/json"},
                body=dumps(
                    [
                        {
                            "status": "success",
                            "description": "Successful status",
                            "target_url": "url",
                            "name": "name",
                            "finished_at": None,
                            "created_at": None,
                        }
                    ]
                ),
            )
        )
        res = await valid_handler.get_commit_statuses(
            "c739768fcac68144a3a6d82305b9c4106934d31a"
        )
        assert res == "success"
