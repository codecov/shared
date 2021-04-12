import pickle

from shared.torngit.exceptions import TorngitClientError


def test_pickle_torngit_client_error():
    error = TorngitClientError("code", "response", "message")
    text = pickle.dumps(error)
    renegerated_error = pickle.loads(text)
    assert isinstance(renegerated_error, TorngitClientError)
    assert renegerated_error.code == error.code
    assert renegerated_error.response == error.response
    assert renegerated_error.message == error.message
