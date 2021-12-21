import socket
from json import dumps

import pytest

from shared.torngit.base import TokenType
from shared.torngit.exceptions import TorngitServerUnreachableError
from shared.torngit.gitlab import Gitlab


@pytest.fixture
def valid_handler():
    return Gitlab(
        repo=dict(service_id="187725", name="codecov-test"),
        owner=dict(username="ThiagoCodecov", service_id="109479"),
        token=dict(key="some_key"),
    )


class TestUnitGitlab(object):
    @pytest.mark.asyncio
    async def test_get_commit_statuses(self, mocker, valid_handler):
        mocked_fetch = mocker.patch.object(
            Gitlab,
            "api",
            return_value=[
                {
                    "status": "success",
                    "description": "Successful status",
                    "target_url": "url",
                    "name": "name",
                    "finished_at": None,
                    "created_at": None,
                },
                {
                    "status": None,
                    "description": "None status",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
            ],
        )
        res = await valid_handler.get_commit_statuses(
            "c739768fcac68144a3a6d82305b9c4106934d31a"
        )
        assert res == "failure"

    @pytest.mark.asyncio
    async def test_get_commit_statuses_success(self, mocker, valid_handler):
        mocked_fetch = mocker.patch.object(
            Gitlab,
            "api",
            return_value=[
                {
                    "status": "success",
                    "description": "Successful status",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
                {
                    "status": "success",
                    "description": "Another successful status",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
                {
                    "status": "skipped",
                    "description": "This was skipped so still counts as success",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
            ],
        )
        res = await valid_handler.get_commit_statuses(
            "c739768fcac68144a3a6d82305b9c4106934d31a"
        )
        assert res == "success"

    @pytest.mark.asyncio
    async def test_get_commit_statuses_pending(self, mocker, valid_handler):
        mocked_fetch = mocker.patch.object(
            Gitlab,
            "api",
            return_value=[
                {
                    "status": "created",
                    "description": "Created means still pending",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
                {
                    "status": "manual",
                    "description": "This requires a manual run so we'll consider it pending until then",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
                {
                    "status": "waiting_for_resource",
                    "description": "Waiting for a resource",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
            ],
        )
        res = await valid_handler.get_commit_statuses(
            "c739768fcac68144a3a6d82305b9c4106934d31a"
        )
        assert res == "pending"

    @pytest.mark.asyncio
    async def test_find_pull_request_by_commit_new_endpoint_doesnt_find_old_does(
        self, mocker, valid_handler
    ):
        commit_sha = "c739768fcac68144a3a6d82305b9c4106934d31a"
        first_result = []
        second_result = [{"sha": "aaaa", "iid": 123}, {"sha": commit_sha, "iid": 986}]
        results = [first_result, second_result]
        mocker.patch.object(Gitlab, "api", side_effect=results)
        res = await valid_handler.find_pull_request(commit_sha)
        assert res == 986

    def test_get_token_by_type_if_none(self):
        instance = Gitlab(
            token="token",
            token_type_mapping={
                TokenType.read: "read",
                TokenType.admin: "admin",
                TokenType.comment: None,
                TokenType.status: "status",
            },
        )
        assert instance.get_token_by_type_if_none(None, TokenType.read) == "read"
        assert instance.get_token_by_type_if_none(None, TokenType.admin) == "admin"
        assert instance.get_token_by_type_if_none(None, TokenType.comment) == "token"
        assert instance.get_token_by_type_if_none(None, TokenType.status) == "status"
        assert instance.get_token_by_type_if_none(
            {"key": "token_set_user"}, TokenType.read
        ) == {"key": "token_set_user"}
        assert instance.get_token_by_type_if_none(
            {"key": "token_set_user"}, TokenType.admin
        ) == {"key": "token_set_user"}
        assert instance.get_token_by_type_if_none(
            {"key": "token_set_user"}, TokenType.comment
        ) == {"key": "token_set_user"}
        assert instance.get_token_by_type_if_none(
            {"key": "token_set_user"}, TokenType.status
        ) == {"key": "token_set_user"}
