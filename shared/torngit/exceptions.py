class TorngitError(Exception):
    pass


class TorngitClientError(TorngitError):
    @property
    def code(self):
        return self._code


class TorngitClientGeneralError(TorngitClientError):
    def __init__(self, status_code, response, message):
        super().__init__(status_code, response, message)
        self._code = status_code
        self.response = response
        self.message = message


class TorngitRepoNotFoundError(TorngitClientError):
    def __init__(self, response, message):
        super().__init__(response, message)
        self._code = 404
        self.response = response


class TorngitObjectNotFoundError(TorngitClientError):
    def __init__(self, response, message):
        super().__init__(response, message)
        self._code = 404
        self.response = response
        self.message = message


class TorngitRateLimitError(TorngitClientError):
    def __init__(self, response, message, reset):
        super().__init__(response, message, reset)
        self.reset = reset
        self._code = 403
        self.message = message


class TorngitUnauthorizedError(TorngitClientError):
    def __init__(self, response, message):
        super().__init__(response, message)
        self._code = 401


class TorngitServerFailureError(TorngitError):
    pass


class TorngitServerUnreachableError(TorngitServerFailureError):
    pass


class TorngitServer5xxCodeError(TorngitServerFailureError):
    pass
