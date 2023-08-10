from shared.metrics import metrics
from shared.utils.test_utils import mock_metrics


class TestMockMetrics(object):
    def test_mock_metrics_incr_decr(self, mocker):
        m = mock_metrics(mocker)

        metrics.incr("foo", count=33)
        assert m.data["foo"] == 33

        metrics.decr("foo", count=15)
        assert m.data["foo"] == 33 - 15
