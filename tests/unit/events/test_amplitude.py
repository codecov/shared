from unittest.mock import Mock, patch

from django.test import override_settings

from shared.events.amplitude import UNKNOWN_USER_OWNERID, AmplitudeEventPublisher
from shared.events.amplitude.metrics import (
    AMPLITUDE_PUBLISH_COUNTER,
    AMPLITUDE_PUBLISH_FAILURE_COUNTER,
)
from shared.events.amplitude.publisher import StubbedAmplitudeClient


@override_settings(AMPLITUDE_API_KEY="asdf1234")
@patch("shared.events.amplitude.publisher.EventOptions")
@patch("shared.events.amplitude.publisher.Amplitude")
def test_set_orgs(amplitude_mock, event_options_mock):
    amplitude = AmplitudeEventPublisher(override_env=True)

    amplitude.client.set_group = Mock()
    event_options_mock.return_value = "mock_event_options"

    amplitude.publish("set_orgs", {"user_ownerid": 123, "org_ids": [1, 32]})

    amplitude_mock.assert_called_once()
    amplitude.client.set_group.assert_called_once_with(
        group_type="org", group_name=["1", "32"], event_options="mock_event_options"
    )
    event_options_mock.assert_called_once_with(user_id="123")


@override_settings(AMPLITUDE_API_KEY="asdf1234")
@patch("shared.events.amplitude.publisher.EventOptions")
@patch("shared.events.amplitude.publisher.Amplitude")
def test_set_orgs_returns_early_when_anonymous_user(amplitude_mock, event_options_mock):
    amplitude = AmplitudeEventPublisher(override_env=True)

    amplitude.client.set_group = Mock()
    event_options_mock.return_value = "mock_event_options"

    amplitude.publish(
        "set_orgs", {"user_ownerid": UNKNOWN_USER_OWNERID, "org_ids": [1, 32]}
    )

    amplitude_mock.assert_called_once()
    amplitude.client.set_group.assert_not_called()
    event_options_mock.assert_not_called()


@override_settings(AMPLITUDE_API_KEY="asdf1234")
@patch("shared.events.amplitude.publisher.Amplitude")
@patch("shared.events.amplitude.publisher.inc_counter")
def test_set_orgs_throws_when_missing_org_ids(mock_inc_counter, _):
    amplitude = AmplitudeEventPublisher(override_env=True)

    amplitude.publish("set_orgs", {"user_ownerid": 123})

    mock_inc_counter.assert_called_with(
        AMPLITUDE_PUBLISH_FAILURE_COUNTER,
        labels={"event_type": "set_orgs", "error": "MissingEventPropertyException"},
    )


@override_settings(AMPLITUDE_API_KEY="asdf1234")
@patch("shared.events.amplitude.publisher.BaseEvent")
@patch("shared.events.amplitude.publisher.Amplitude")
def test_publish(amplitude_mock, base_event_mock):
    amplitude = AmplitudeEventPublisher(override_env=True)

    amplitude.client.track = Mock()

    amplitude.publish("App Installed", {"user_ownerid": 123, "ownerid": 321})

    amplitude_mock.assert_called_once()
    amplitude.client.track.assert_called_once()
    base_event_mock.assert_called_once_with(
        "App Installed",
        user_id="123",
        event_properties={"ownerid": 321},
        groups={"org": 321},
    )


@override_settings(AMPLITUDE_API_KEY="asdf1234")
@patch("shared.events.amplitude.publisher.BaseEvent")
@patch("shared.events.amplitude.publisher.Amplitude")
@patch("shared.events.amplitude.publisher.inc_counter")
def test_publish_increments_counter(mock_inc_counter, amplitude_mock, base_event_mock):
    amplitude = AmplitudeEventPublisher(override_env=True)

    amplitude.client.track = Mock()

    amplitude.publish("App Installed", {"user_ownerid": 123, "ownerid": 321})

    amplitude_mock.assert_called_once()
    amplitude.client.track.assert_called_once()
    base_event_mock.assert_called_once_with(
        "App Installed",
        user_id="123",
        event_properties={"ownerid": 321},
        groups={"org": 321},
    )
    mock_inc_counter.assert_called_once_with(
        AMPLITUDE_PUBLISH_COUNTER, labels={"event_type": "App Installed"}
    )


@override_settings(AMPLITUDE_API_KEY="asdf1234")
@patch("shared.events.amplitude.publisher.BaseEvent")
@patch("shared.events.amplitude.publisher.Amplitude")
def test_publish_removes_extra_properties(amplitude_mock, base_event_mock):
    amplitude = AmplitudeEventPublisher(override_env=True)

    amplitude.client.track = Mock()

    amplitude.publish(
        "App Installed", {"user_ownerid": 123, "ownerid": 321, "repoid": 9}
    )

    amplitude_mock.assert_called_once()
    amplitude.client.track.assert_called_once()
    base_event_mock.assert_called_once_with(
        "App Installed",
        user_id="123",
        event_properties={"ownerid": 321},
        groups={"org": 321},
    )


@override_settings(AMPLITUDE_API_KEY="asdf1234")
@patch("shared.events.amplitude.publisher.BaseEvent")
@patch("shared.events.amplitude.publisher.Amplitude")
def test_publish_converts_to_camel_case(amplitude_mock, base_event_mock):
    amplitude = AmplitudeEventPublisher(override_env=True)

    amplitude.client.track = Mock()

    amplitude.publish(
        "Upload Received",
        {
            "user_ownerid": 123,
            "ownerid": 321,
            "repoid": 132,
            "commitid": 12,
            "pullid": None,
            "upload_type": "Coverage report",
        },
    )

    amplitude_mock.assert_called_once()
    amplitude.client.track.assert_called_once()
    base_event_mock.assert_called_once_with(
        "Upload Received",
        user_id="123",
        event_properties={
            "ownerid": 321,
            "repoid": 132,
            "commitid": 12,
            "pullid": None,
            "uploadType": "Coverage report",
        },
        groups={
            "org": 321,
        },
    )


@override_settings(AMPLITUDE_API_KEY="asdf1234")
@patch("shared.events.amplitude.publisher.BaseEvent")
@patch("shared.events.amplitude.publisher.Amplitude")
def test_publish_converts_anonymous_owner_id_to_user_id(
    amplitude_mock, base_event_mock
):
    amplitude = AmplitudeEventPublisher(override_env=True)

    amplitude.client.track = Mock()

    amplitude.publish(
        "Upload Received",
        {
            "user_ownerid": UNKNOWN_USER_OWNERID,
            "ownerid": 321,
            "repoid": 132,
            "commitid": 12,
            "pullid": None,
            "upload_type": "Coverage report",
        },
    )

    amplitude_mock.assert_called_once()
    amplitude.client.track.assert_called_once()
    base_event_mock.assert_called_once_with(
        "Upload Received",
        user_id="anon",
        event_properties={
            "ownerid": 321,
            "repoid": 132,
            "commitid": 12,
            "pullid": None,
            "uploadType": "Coverage report",
        },
        groups={
            "org": 321,
        },
    )


@override_settings(AMPLITUDE_API_KEY="asdf1234")
@patch("shared.events.amplitude.publisher.Amplitude")
def test_publish_fails_gracefully(amplitude_mock):
    amplitude = AmplitudeEventPublisher(override_env=True)

    amplitude.client.track = Mock()

    try:
        amplitude.publish("App Installed", {"user_ownerid": 123})
    except Exception:
        assert False

    amplitude_mock.assert_called_once()
    amplitude.client.track.assert_not_called()


@override_settings(AMPLITUDE_API_KEY="asdf1234")
@patch("shared.events.amplitude.publisher.Amplitude")
@patch("shared.events.amplitude.publisher.inc_counter")
def test_publish_missing_required_property(mock_inc_counter, _):
    amplitude = AmplitudeEventPublisher(override_env=True)

    amplitude.client.track = Mock()

    amplitude.publish("App Installed", {"user_ownerid": 123})

    mock_inc_counter.assert_called_with(
        AMPLITUDE_PUBLISH_FAILURE_COUNTER,
        labels={
            "event_type": "App Installed",
            "error": "MissingEventPropertyException",
        },
    )


@override_settings(AMPLITUDE_API_KEY=None)
def test_uses_stubbed_amplitude_when_None_api_key():
    amplitude = AmplitudeEventPublisher(override_env=True)

    assert isinstance(amplitude.client, StubbedAmplitudeClient)


@override_settings(AMPLITUDE_API_KEY=None)
@patch("shared.events.amplitude.publisher.Amplitude")
def test_stubbed_amplitude_does_not_call_amplitude(amplitude_mock):
    amplitude = AmplitudeEventPublisher(override_env=True)

    amplitude.publish("User Created", {"user_ownerid": 123})
    amplitude.publish("set_orgs", {"user_ownerid": 123, "org_ids": [1, 32]})

    amplitude_mock.assert_not_called()
