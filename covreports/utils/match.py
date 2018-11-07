import re


def match(patterns, string):
    if patterns is None or string in patterns:
        return True

    patterns = set([_f for _f in patterns if _f])
    negatives = [a for a in patterns if a.startswith(('^!', '!'))]
    positives = patterns - set(negatives)

    # must not match
    for pattern in negatives:
        # matched a negative search
        if re.match(pattern.replace('!', ''), string):
            return False

    if positives:
        for pattern in positives:
            # match was found
            if re.match(pattern, string):
                return True

        # did not match any required paths
        return False

    else:
        # no positives: everyting else is ok
        return True


def match_any(patterns, match_any_of_these):
    if match_any_of_these:
        for string in match_any_of_these:
            if match(patterns, string):
                return True
    return False
