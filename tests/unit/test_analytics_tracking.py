from mock import patch

from shared.analytics_tracking import on_error, setup_analytics, track_event, track_user
from tests.base import BaseTestCase


class TestAnalyticsTracking(BaseTestCase):
    def test_track_event(self, mocker):
        mock_track = mocker.patch("shared.analytics_tracking.analytics.track")
        mocker.patch("shared.analytics_tracking.segment_enabled", True)

        track_event("123", "Coverage Report Passed", {"test": True})
        assert mock_track.called

    def test_track_event_invalid_name(self, mocker):
        mock_track = mocker.patch("shared.analytics_tracking.analytics.track")
        mocker.patch("shared.analytics_tracking.segment_enabled", True)

        track_event("123", "Invalid Name", {"test": True})
        assert not mock_track.called

    def test_track_event_segment_disabled(self, mocker):
        mocker.patch("shared.analytics_tracking.segment_enabled", False)
        mock_track = mocker.patch("shared.analytics_tracking.analytics.track")

        track_event("123", "Coverage Report Failed", {"test": True})
        assert not mock_track.called

    def test_track_event_is_enterprise(self, mocker):
        mock_track = mocker.patch("shared.analytics_tracking.analytics.track")
        mocker.patch("shared.analytics_tracking.segment_enabled", True)

        track_event("123", "Coverage Report Failed", {"test": True}, True)
        assert not mock_track.called

    def test_track_user(self, mocker):
        mock_identify = mocker.patch("shared.analytics_tracking.analytics.identify")
        mocker.patch("shared.analytics_tracking.segment_enabled", True)

        track_user("456", {"username": "test"})
        assert mock_identify.called

    def test_track_user_segment_disabled(self, mocker):
        mock_identify = mocker.patch("shared.analytics_tracking.analytics.identify")
        mocker.patch("shared.analytics_tracking.segment_enabled", False)

        track_user("456", {"username": "test"})
        assert not mock_identify.called

    @patch("shared.analytics_tracking.analytics.identify")
    def test_track_user_is_enterprise(self, mocker):
        mock_identify = mocker.patch("shared.analytics_tracking.analytics.identify")
        mocker.patch("shared.analytics_tracking.segment_enabled", True)

        track_user("456", {"username": "test"}, True)
        assert not mock_identify.called

    def test_on_error(self):
        on_error("Not initialized with API key")

    def test_setup_analytics(self, mock_configuration):
        mock_configuration.set_params(
            {"setup": {"debug": True, "segment": {"key": "123"}}}
        )
        setup_analytics()
