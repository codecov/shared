from mock import patch

from tests.base import BaseTestCase
from shared.analytics_tracking import track_event, track_user, on_error, setup_analytics


class TestAnalyticsTracking(BaseTestCase):
    @patch("shared.analytics_tracking.analytics.track")
    def test_track_event(self, mock_track):
        with patch("shared.analytics_tracking.segment_enabled", True):
            track_event("123", "Coverage Report Passed", {"test": True})
            assert mock_track.called

    @patch("shared.analytics_tracking.analytics.track")
    def test_track_event_invalid_name(self, mock_track):
        with patch("shared.analytics_tracking.segment_enabled", True):
            track_event("123", "Invalid Name", {"test": True})
            assert not mock_track.called

    @patch("shared.analytics_tracking.analytics.track")
    def test_track_event_segment_disabled(self, mock_track):
        with patch("shared.analytics_tracking.segment_enabled", False):
            track_event("123", "Coverage Report Failed", {"test": True})
            assert not mock_track.called

    @patch("shared.analytics_tracking.analytics.track")
    def test_track_event_is_enterprise(self, mock_track):
        with patch("shared.analytics_tracking.segment_enabled", False):
            track_event("123", "Coverage Report Failed", {"test": True}, True)
            assert not mock_track.called

    @patch("shared.analytics_tracking.analytics.identify")
    def test_track_user(self, mock_identify):
        with patch("shared.analytics_tracking.segment_enabled", True):
            track_user("456", {"username": "test"})
            assert mock_identify.called

    @patch("shared.analytics_tracking.analytics.identify")
    def test_track_user_segment_disabled(self, mock_identify):
        with patch("shared.analytics_tracking.segment_enabled", False):
            track_user("456", {"username": "test"})
            assert not mock_identify.called

    @patch("shared.analytics_tracking.analytics.identify")
    def test_track_user_is_enterprise(self, mock_identify):
        with patch("shared.analytics_tracking.segment_enabled", False):
            track_user("456", {"username": "test"}, True)
            assert not mock_identify.called

    def test_on_error(self):
        on_error("Not initialized with API key")

    def test_setup_analytics(self, mock_configuration):
        mock_configuration.set_params(
            {"setup": {"debug": True, "segment": {"key": "123"}}}
        )
        setup_analytics()
