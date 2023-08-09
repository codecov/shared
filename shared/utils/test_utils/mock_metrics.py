from collections import defaultdict

from shared.metrics import metrics as orig_metrics


class MockMetrics:
    def __init__(self, mocker):
        self.data = defaultdict(int)
        mocker.patch.object(orig_metrics, "incr", self._incr)
        mocker.patch.object(orig_metrics, "decr", self._decr)

    def _incr(self, stat, count=1, rate=1):
        self.data[stat] += count

    def _decr(self, stat, count=1, rate=1):
        self.data[stat] -= count


def mock_metrics(mocker):
    return MockMetrics(mocker)
