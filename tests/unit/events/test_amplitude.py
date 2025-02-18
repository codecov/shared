from unittest.mock import Mock, patch

from django.test import override_settings
from pytest import raises

from shared.events.amplitude import AmplitudeEventPublisher
from shared.events.amplitude.publisher import StubbedAmplitudeClient
from shared.events.base import (
    MissingEventPropertyException,
)


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
@patch("shared.events.amplitude.publisher.Amplitude")
def test_set_orgs_throws_when_missing_org_ids(_):
    amplitude = AmplitudeEventPublisher(override_env=True)

    with raises(MissingEventPropertyException):
        amplitude.publish("set_orgs", {"user_ownerid": 123})


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
        "Upload Sent",
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
        "Upload Sent",
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
@patch("shared.events.amplitude.publisher.Amplitude")
def test_publish_missing_required_property(_):
    amplitude = AmplitudeEventPublisher(override_env=True)

    amplitude.client.track = Mock()

    with raises(MissingEventPropertyException):
        amplitude.publish("App Installed", {"user_ownerid": 123})


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
