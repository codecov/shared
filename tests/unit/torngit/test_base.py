from shared.torngit.base import TorngitBaseAdapter, TokenType


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
        instance = TorngitBaseAdapter(token={"key": "token"},)
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
