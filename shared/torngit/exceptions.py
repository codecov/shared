class TorngitError(Exception):
    pass


class TorngitMisconfiguredCredentials(TorngitError):
    pass


class TorngitClientError(TorngitError):
    @property
    def code(self):
        return self._code

    @property
    def response_data(self):
        return self._response_data


class TorngitMaxRetriesError(TorngitClientError):
    pass


class TorngitClientGeneralError(TorngitClientError):
    def __init__(self, status_code, response_data, message):
        super().__init__(status_code, response_data, message)
        self._code = status_code
        self._response_data = response_data
        self.message = message


class TorngitRepoNotFoundError(TorngitClientError):
    def __init__(self, response_data, message):
        super().__init__(response_data, message)
        self._code = 404
        self._response_data = response_data
        self.message = message


class TorngitObjectNotFoundError(TorngitClientError):
    def __init__(self, response_data, message):
        super().__init__(response_data, message)
        self._code = 404
        self._response_data = response_data
        self.message = message


class TorngitRateLimitError(TorngitClientError):
    def __init__(self, response_data, message, reset=None, retry_after=None):
        super().__init__(response_data, message, reset)
        self._code = 403
        self._response_data = response_data
        self.message = message

        # timestamp when the rate limit resets
        self.reset = reset
        # seconds to wait before making another request
        self.retry_after = retry_after


class TorngitUnauthorizedError(TorngitClientError):
    def __init__(self, response_data, message):
        super().__init__(response_data, message)
        self._code = 401
        self._response_data = response_data
        self.message = message


class TorngitServerFailureError(TorngitError):
    pass


class TorngitServerUnreachableError(TorngitServerFailureError):
    pass


class TorngitServer5xxCodeError(TorngitServerFailureError):
    pass


class TorngitRefreshTokenFailedError(TorngitError):
    def __init__(self, message) -> None:
        self._code = 555
        self._response_data = None
        self.message = message


class TorngitCantRefreshTokenError(TorngitClientError):
    def __init__(self, message) -> None:
        self._code = 555
        self._response_data = None
        self.message = message
