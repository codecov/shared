from typing import List, Optional, Tuple
    def get_token_by_type_if_none(self, token: Optional[str], token_type: TokenType):
        if token is not None:
            return token
        return self.get_token_by_type(token_type)

            _diff = _diff.replace("\r\n", "\n").split("\n")
            if _diff[-1] == "":
                # if the diff ends in a '\n' character then we'll have an extra
                # empty line at the end that we don't want
                _diff.pop()
                    continue