import re
from collections import defaultdict


def matches(string, pattern):
    if pattern == string:
        return True
    else:
        if '*' in pattern:
            return re.match('^'+pattern.replace('*', '.*')+'$', string) is not None
        return False


class Status(object):
    def __init__(self, statuses):
        # reduce based on time
        contexts = defaultdict(list)
        [contexts[status['context']].append((status['time'], status)) for status in statuses]
        contexts = [sorted(context, key=lambda (t, d): t)[-1][1] for context in contexts.values()]
        self._statuses = contexts
        states = set(map(lambda s: s['state'], contexts))
        self._state = 'failure' if 'failure' in states \
                      else 'pending' if 'pending' in states \
                      else 'success'

    def __sub__(self, context):
        """Remove ci status from list, return new object"""
        return Status(filter(lambda s: not matches(s['context'], context), self._statuses))

    def __eq__(self, other):
        """Returns the current ci status"""
        assert other in ('success', 'failure', 'pending')
        return self._state == other

    def __str__(self):
        """Returns the current ci status"""
        return self._state

    @property
    def is_pending(self):
        return self._state == 'pending'

    @property
    def is_success(self):
        return self._state == 'success'

    @property
    def is_failure(self):
        return self._state == 'failure'

    def __len__(self):
        return len(self._statuses)

    def __contains__(self, context):
        for c in self._statuses:
            if matches(c['context'], context):
                return True
        return False

    def filter(self, method):
        return Status(filter(method, self._statuses))

    @property
    def pending(self):
        # return list of pending statuses
        return [status for status in self._statuses if status['state'] == 'pending']

    def get(self, context):
        for status in self._statuses:
            if status['context'] == context:
                return status
