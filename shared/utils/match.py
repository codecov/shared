import re
from typing import Sequence


class Matcher:
    def __init__(self, patterns: Sequence[str] | None):
        self._patterns = set(patterns or [])
        self._is_initialized = False
        # a list of patterns that will result in `True` on a match
        self._positives: list[re.Pattern] = []
        # a list of patterns that will result in `False` on a match
        self._negatives: list[re.Pattern] = []

    def _get_matchers(self) -> tuple[list[re.Pattern], list[re.Pattern]]:
        if not self._is_initialized:
            for pattern in self._patterns:
                if not pattern:
                    continue
                if pattern.startswith(("^!", "!")):
                    self._negatives.append(re.compile(pattern.replace("!", "")))
                else:
                    self._positives.append(re.compile(pattern))
            self._is_initialized = True

        return self._positives, self._negatives

    def match(self, s: str) -> bool:
        if not self._patterns or s in self._patterns:
            return True

        positives, negatives = self._get_matchers()

        # must not match
        for pattern in negatives:
            # matched a negative search
            if pattern.match(s):
                return False

        if positives:
            for pattern in positives:
                # match was found
                if pattern.match(s):
                    return True

            # did not match any required paths
            return False

        else:
            # no positives: everything else is ok
            return True

    def match_any(self, strings: Sequence[str] | None) -> bool:
        if not strings:
            return False
        return any(self.match(s) for s in strings)


def match(patterns: Sequence[str] | None, string: str):
    matcher = Matcher(patterns)
    return matcher.match(string)


def match_any(
    patterns: Sequence[str] | None, match_any_of_these: Sequence[str] | None
) -> bool:
    matcher = Matcher(patterns)
    return matcher.match_any(match_any_of_these)
