import pytest
from unittest.mock import AsyncMock, MagicMock
from shared.torngit.github import build_comment_request_body

class TestGithubComments:
    @pytest.mark.asyncio
    async def test_build_comment_request_body_with_generate_tests_action(self):
        # Arrange
        comment = "Test comment"
        bot_name = "codecov-bot"
        is_bot_comment = True
        is_pull = True
        is_analysis_requested = True
        has_commit_data = True
        include_button = True
        comment_header = "Comment header"
        comment_footer = "Comment footer"
        repo = MagicMock()

        # Act
        result = await build_comment_request_body(
            comment, bot_name, is_bot_comment, is_pull, is_analysis_requested,
            has_commit_data, include_button, comment_header, comment_footer, repo
        )

        # Assert
        assert "actions" in result
        assert len(result["actions"]) == 1
        action = result["actions"][0]
        assert action["name"] == "Generate Tests"
        assert action["type"] == "copilot-chat"
        assert action["prompt"] == f"@{bot_name} generate tests for PR"
        assert result["body"] == f"{comment_header}\n{comment}\n{comment_footer}"
