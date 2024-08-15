import pickle

from shared.torngit.exceptions import (
    TorngitClientGeneralError,
    TorngitObjectNotFoundError,
    TorngitRateLimitError,
    TorngitRepoNotFoundError,
    TorngitUnauthorizedError,
)


def test_pickle_torngitclientgeneralerror():
    status_code, response, message = 400, "response", "message"
    error = TorngitClientGeneralError(
        status_code, response_data=response, message=message
    )
    text = pickle.dumps(error)
    renegerated_error = pickle.loads(text)
    assert isinstance(renegerated_error, TorngitClientGeneralError)
    assert renegerated_error.code == error.code


def test_pickle_torngitreponotfounderror():
    response, message = "response", "message"
    error = TorngitRepoNotFoundError(response_data=response, message=message)
    text = pickle.dumps(error)
    renegerated_error = pickle.loads(text)
    assert isinstance(renegerated_error, TorngitRepoNotFoundError)
    assert renegerated_error.code == error.code


def test_pickle_torngitobjectnotfounderror():
    response, message = "response", "message"
    error = TorngitObjectNotFoundError(response_data=response, message=message)
    text = pickle.dumps(error)
    renegerated_error = pickle.loads(text)
    assert isinstance(renegerated_error, TorngitObjectNotFoundError)
    assert renegerated_error.code == error.code


def test_pickle_torngitratelimiterror():
    reset_time, response, message = 10000000, "response", "message"
    error = TorngitRateLimitError(
        response_data=response, message=message, reset=reset_time
    )
    text = pickle.dumps(error)
    renegerated_error = pickle.loads(text)
    assert isinstance(renegerated_error, TorngitRateLimitError)
    assert renegerated_error.code == error.code


def test_pickle_torngitunauthorizederror():
    response, message = "response", "message"
    error = TorngitUnauthorizedError(response_data=response, message=message)
    text = pickle.dumps(error)
    renegerated_error = pickle.loads(text)
    assert isinstance(renegerated_error, TorngitUnauthorizedError)
    assert renegerated_error.code == error.code
