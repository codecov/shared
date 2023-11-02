import httpx
import pytest
import respx

from shared.analytics_tracking.events import Event, Events
from shared.analytics_tracking.marketo import Marketo, MarketoError
from shared.config import ConfigHelper


class TestMarketo(object):
    @pytest.fixture
    def mock_setup(self, mocker):
        yaml_content = "\n".join(
            [
                "setup:",
                "  marketo:",
                "    enabled: true",
                "    client_id: 1234",
                "    client_secret: secret",
                "    base_url: https://marketo/test",
            ]
        )
        mocker.patch.object(ConfigHelper, "load_yaml_file", return_value=yaml_content)
        this_config = ConfigHelper()
        mocker.patch("shared.config._get_config_instance", return_value=this_config)

    @pytest.mark.asyncio
    def test_make_rest_request(self, mocker, mock_setup):
        with respx.mock:
            token_request = respx.get(
                "https://marketo/test/identity/oauth/token?grant_type=client_credentials&client_id=1234&client_secret=secret"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    json={
                        "access_token": "test1657-1111-2222-3333-444444444444:int",
                        "token_type": "bearer",
                        "expires_in": 3599,
                        "scope": "apis@acmeinc.com",
                    },
                )
            )
            marketo_request = respx.get("https://marketo/test/path/url").mock(
                return_value=httpx.Response(
                    status_code=200,
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "1350085394",
                    },
                    json={
                        "requestId": "e42b#14272d07d78",
                        "success": True,
                        "result": [
                            {
                                "id": 318581,
                                "updatedAt": "2015-06-11T23:15:23Z",
                                "lastName": "Doe",
                                "email": "jdoe@marketo.com",
                                "createdAt": "2015-03-17T00:18:40Z",
                                "firstName": "John",
                            }
                        ],
                    },
                )
            )
            marketo = Marketo()
            url = "/path/url"
            response = marketo.make_rest_request(url)
            assert response == {
                "requestId": "e42b#14272d07d78",
                "success": True,
                "result": [
                    {
                        "id": 318581,
                        "updatedAt": "2015-06-11T23:15:23Z",
                        "lastName": "Doe",
                        "email": "jdoe@marketo.com",
                        "createdAt": "2015-03-17T00:18:40Z",
                        "firstName": "John",
                    }
                ],
            }

    @pytest.mark.asyncio
    def test_track_event(self, mocker, mock_setup):
        class uuid(object):
            bytes = b"\x00\x01\x02"

        with respx.mock:
            token_request = respx.get(
                "https://marketo/test/identity/oauth/token?grant_type=client_credentials&client_id=1234&client_secret=secret"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    json={
                        "access_token": "test1657-1111-2222-3333-444444444444:int",
                        "token_type": "bearer",
                        "expires_in": 3599,
                        "scope": "apis@acmeinc.com",
                    },
                )
            )
            marketo_request = respx.post(
                "https://marketo/test/rest/v1/leads.json"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "1350085394",
                    },
                    json={
                        "requestId": "e42b#14272d07d78",
                        "success": True,
                        "result": [
                            {
                                "id": 318581,
                                "updatedAt": "2015-06-11T23:15:23Z",
                                "lastName": "Doe",
                                "email": "jdoe@marketo.com",
                                "createdAt": "2015-03-17T00:18:40Z",
                                "firstName": "John",
                            }
                        ],
                    },
                )
            )
            mocker.patch("shared.analytics_tracking.events.uuid1", return_value=uuid)
            event = Event(
                Events.ACCOUNT_UPLOADED_COVERAGE_REPORT.value,
                user_id="1234",
                repo_id="1234",
                branch="test_branch",
            )
            marketo = Marketo()
            response = marketo.track_event(event, is_enterprise=False, context=None)
            assert response == {
                "requestId": "e42b#14272d07d78",
                "success": True,
                "result": [
                    {
                        "id": 318581,
                        "updatedAt": "2015-06-11T23:15:23Z",
                        "lastName": "Doe",
                        "email": "jdoe@marketo.com",
                        "createdAt": "2015-03-17T00:18:40Z",
                        "firstName": "John",
                    }
                ],
            }

    @pytest.mark.asyncio
    def test_make_failed_rest_request(self, mocker, mock_setup):
        with respx.mock:
            token_request = respx.get(
                "https://marketo/test/identity/oauth/token?grant_type=client_credentials&client_id=1234&client_secret=secret"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    json={
                        "access_token": "test1657-1111-2222-3333-444444444444:int",
                        "token_type": "bearer",
                        "expires_in": 3599,
                        "scope": "apis@acmeinc.com",
                    },
                )
            )
            marketo_request = respx.get("https://marketo/test/path/url").mock(
                return_value=httpx.Response(
                    status_code=200,
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "1350085394",
                    },
                    json={
                        "requestId": "e42b#14272d07d78",
                        "success": False,
                        "errors": [{"code": "601", "message": "Unauthorized"}],
                    },
                )
            )
            marketo = Marketo()
            url = "/path/url"
            with pytest.raises(MarketoError) as exc:
                response = marketo.make_rest_request(url)
            assert exc.value.code == "601"
            assert exc.value.message == "Unauthorized"

    @pytest.mark.asyncio
    def test_make_rest_request_failed_record_level(self, mocker, mock_setup):
        with respx.mock:
            token_request = respx.get(
                "https://marketo/test/identity/oauth/token?grant_type=client_credentials&client_id=1234&client_secret=secret"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    json={
                        "access_token": "test1657-1111-2222-3333-444444444444:int",
                        "token_type": "bearer",
                        "expires_in": 3599,
                        "scope": "apis@acmeinc.com",
                    },
                )
            )
            marketo_request = respx.get("https://marketo/test/path/url").mock(
                return_value=httpx.Response(
                    status_code=200,
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "1350085394",
                    },
                    json={
                        "requestId": "e42b#14272d07d78",
                        "success": True,
                        "result": [
                            {"id": 50, "status": "created"},
                            {"id": 51, "status": "created"},
                            {
                                "status": "skipped",
                                "reasons": [
                                    {"code": "1005", "message": "Lead already exists"}
                                ],
                            },
                        ],
                    },
                )
            )
            marketo = Marketo()
            url = "/path/url"
            with pytest.raises(MarketoError) as exc:
                response = marketo.make_rest_request(url)
            assert exc.value.code == "1005"
            assert exc.value.message == "Lead already exists"
