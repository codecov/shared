class TorngitError(Exception):
    pass


class TorngitClientError(TorngitError):
    def __init__(self, code, response, message):
        super().__init__(code, response, message)
        self.code = code
        self.response = response
        self.message = message


class TorngitRepoNotFoundError(TorngitClientError):
    def __init__(self, response, message):
        code = 404
        super().__init__(code, response, message)


class TorngitObjectNotFoundError(TorngitClientError):
    def __init__(self, response, message):
        code = 404
        super().__init__(code, response, message)


class TorngitRateLimitError(TorngitClientError):
    def __init__(self, response, message, reset):
        code = 403
        super().__init__(code, response, message)
        self.reset = reset


class TorngitUnauthorizedError(TorngitClientError):
    def __init__(self, response, message):
        code = 401
        super().__init__(code, response, message)


class TorngitServerFailureError(TorngitError):
    pass


class TorngitServerUnreachableError(TorngitServerFailureError):
    pass


class TorngitServer5xxCodeError(TorngitServerFailureError):
    pass
