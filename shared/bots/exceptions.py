class RequestedGithubAppNotFound(Exception):
    pass


class OwnerWithoutValidBotError(Exception):
    pass


class NoConfiguredAppsAvailable(Exception):
    def __init__(
        self, apps_count: int, rate_limited_count: int, suspended_count: int
    ) -> None:
        self.apps_count = apps_count
        self.rate_limited_count = rate_limited_count
        self.suspended_count = suspended_count


class RepositoryWithoutValidBotError(Exception):
    pass
