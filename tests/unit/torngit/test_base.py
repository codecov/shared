import textwrap

import pytest

from shared.torngit.base import TokenType, TorngitBaseAdapter


class TestTorngitBaseAdapter(object):
    def test_get_token_by_type(self):
        instance = TorngitBaseAdapter(
            token={"key": "token"},
            token_type_mapping={
                TokenType.read: {"key": "read"},
                TokenType.admin: {"key": "admin"},
                TokenType.comment: {"key": "comment"},
                TokenType.status: {"key": "status"},
            },
        )
        assert instance.get_token_by_type(TokenType.read) == {"key": "read"}
        assert instance.get_token_by_type(TokenType.admin) == {"key": "admin"}
        assert instance.get_token_by_type(TokenType.comment) == {"key": "comment"}
        assert instance.get_token_by_type(TokenType.status) == {"key": "status"}

    def test_get_token_by_type_no_mapping(self):
        instance = TorngitBaseAdapter(token={"key": "token"})
        assert instance.get_token_by_type(TokenType.read) == {"key": "token"}
        assert instance.get_token_by_type(TokenType.admin) == {"key": "token"}
        assert instance.get_token_by_type(TokenType.comment) == {"key": "token"}
        assert instance.get_token_by_type(TokenType.status) == {"key": "token"}

    def test_get_token_some_mapping(self):
        instance = TorngitBaseAdapter(
            token={"key": "token"},
            token_type_mapping={
                TokenType.read: {"key": "read"},
                TokenType.admin: {"key": "admin"},
                TokenType.status: None,
            },
        )
        assert instance.get_token_by_type(TokenType.read) == {"key": "read"}
        assert instance.get_token_by_type(TokenType.admin) == {"key": "admin"}
        assert instance.get_token_by_type(TokenType.comment) == {"key": "token"}
        assert instance.get_token_by_type(TokenType.status) == {"key": "token"}

    def test_no_token(self):
        instance = TorngitBaseAdapter()
        with pytest.raises(Exception) as exp:
            instance.token
        assert str(exp.value) == "Oauth consumer token not present"

    def test_diff_to_json_no_newline(self):
        instance = TorngitBaseAdapter()
        diff = textwrap.dedent(
            """
            diff --git a/test/file.txt b/test/file.txt
            index 8695aedf2b..e0d2b1e89d 100644
            --- a/test/file.txt
            +++ b/test/file.txt
            @@ -1 +1 @@
            -before
            \\ No newline at end of file
            +after
            \\ No newline at end of file
            """
        )

        res = instance.diff_to_json(diff)
        assert res == {
            "files": {
                "test/file.txt": {
                    "before": None,
                    "segments": [
                        {
                            "header": ["1", "", "1", ""],
                            "lines": ["-before", "+after"],
                        }
                    ],
                    "stats": {
                        "added": 1,
                        "removed": 1,
                    },
                    "type": "modified",
                }
            }
        }

    def test_diff_to_json_unicode_line_separator(self):
        instance = TorngitBaseAdapter()
        diff = textwrap.dedent(
            """
            diff --git a/test/file.txt b/test/file.txt
            index 8695aedf2b..e0d2b1e89d 100644
            --- a/test/file.txt
            +++ b/test/file.txt
            @@ -2,3 +2,3 @@
             first line
            -before\u2028
            +after\u2028
             last line
            """
        )

        res = instance.diff_to_json(diff)
        assert res == {
            "files": {
                "test/file.txt": {
                    "before": None,
                    "segments": [
                        {
                            "header": ["2", "3", "2", "3"],
                            "lines": [
                                " first line",
                                "-before\u2028",
                                "+after\u2028",
                                " last line",
                            ],
                        }
                    ],
                    "stats": {
                        "added": 1,
                        "removed": 1,
                    },
                    "type": "modified",
                }
            }
        }
