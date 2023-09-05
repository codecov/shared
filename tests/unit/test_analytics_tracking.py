import pytest
from mock import patch

from shared.analytics_tracking import get_list_of_analytic_tools, get_tools_manager
from shared.analytics_tracking.events import Events
from shared.analytics_tracking.manager import AnalyticsToolManager


@pytest.fixture
def mock_segment():
    with patch("shared.analytics_tracking.Segment.is_enabled", return_value=True):
        yield


def test_get_list_of_analytic_tools():
    tools = get_list_of_analytic_tools()
    assert isinstance(tools, list)


def test_get_tools_manager(mock_segment):
    tool = get_tools_manager()
    assert tool is not None
    assert isinstance(tool, AnalyticsToolManager)


def test_track_event(mock_segment, mocker):
    analytics_tool = get_tools_manager()
    mock_track = mocker.patch("shared.analytics_tracking.segment.analytics.track")

    analytics_tool.track_event(
        "123",
        Events.USER_SIGNED_IN.value,
        is_enterprise=False,
        event_data={"test": True},
    )

    assert mock_track.called


def test_track_event_tool_not_enabled(mocker):
    analytics_tool = get_tools_manager()
    mock_track = mocker.patch("shared.analytics_tracking.segment.analytics.track")

    analytics_tool.track_event(
        "123",
        Events.USER_SIGNED_UP.value,
        is_enterprise=False,
        event_data={"test": True},
    )

    assert not mock_track.called


def test_track_user(mock_segment, mocker):
    analytics_tool = get_tools_manager()
    mock_identify = mocker.patch("shared.analytics_tracking.segment.analytics.identify")

    user_id = "user123"
    user_data = {"name": "John"}

    analytics_tool.track_user(user_id, user_data=user_data)
    mock_identify.assert_called_once_with(user_id, user_data)


def test_track_event_invalid_name(mock_segment, mocker):
    mock_track = mocker.patch("shared.analytics_tracking.segment.analytics.track")
    analytics_tool = get_tools_manager()

    analytics_tool.track_event(
        "123", "Invalid Name", is_enterprise=False, event_data={"test": True}
    )
    assert not mock_track.called


def test_track_event_is_enterprise(mock_segment, mocker):
    mock_track = mocker.patch("shared.analytics_tracking.segment.analytics.track")
    analytics_tool = get_tools_manager()
    analytics_tool.track_event(
        "123",
        "Account Uploaded Coverage Report",
        is_enterprise=True,
        event_data={"test": True},
    )
    assert not mock_track.called


def test_track_user_is_enterprise(mock_segment, mocker):
    mock_identify = mocker.patch("shared.analytics_tracking.segment.analytics.identify")
    analytics_tool = get_tools_manager()
    analytics_tool.track_user("456", {"username": "test"}, True)
    assert not mock_identify.called


def test_track_account_activated_repo_on_upload(mock_segment, mocker):
    mock_track = mocker.patch("shared.analytics_tracking.segment.analytics.track")
    get_tools_manager().track_account_activated_repo_on_upload(
        repoid="123",
        ownerid="abc",
        commitid="abc123",
        pullid="7",
        is_enterprise=False,
    )
    assert mock_track.called


def test_track_account_activated_repo(mock_segment, mocker):
    mock_track = mocker.patch("shared.analytics_tracking.segment.analytics.track")
    get_tools_manager().track_account_activated_repo(
        repoid="123",
        ownerid="abc",
        commitid="abc123",
        pullid="7",
        is_enterprise=False,
    )
    assert mock_track.called


def test_track_account_uploaded_coverage_report(mock_segment, mocker):
    mock_track = mocker.patch("shared.analytics_tracking.segment.analytics.track")
    get_tools_manager().track_account_uploaded_coverage_report(
        repoid="123",
        ownerid="abc",
        commitid="abc123",
        pullid="7",
        is_enterprise=False,
    )
    assert mock_track.called


def test_track_user_signed_in(mock_segment, mocker):
    mock_track = mocker.patch("shared.analytics_tracking.segment.analytics.track")
    get_tools_manager().track_user_signed_in(
        repoid="123",
        ownerid="abc",
        commitid="abc123",
        pullid="7",
        is_enterprise=False,
        userid=1,
    )
    assert mock_track.called


def test_track_user_signed_up(mock_segment, mocker):
    mock_track = mocker.patch("shared.analytics_tracking.segment.analytics.track")
    get_tools_manager().track_user_signed_up(
        repoid="123",
        ownerid="abc",
        commitid="abc123",
        pullid="7",
        is_enterprise=False,
        userid=1,
    )
    assert mock_track.called
