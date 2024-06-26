class RequestedGithubAppNotFound(Exception):
    pass


class OwnerWithoutValidBotError(Exception):
    pass


class NoConfiguredAppsAvailable(Exception):
    def __init__(self, apps_count: int, all_rate_limited: bool) -> None:
        self.apps_count = apps_count
        self.all_rate_limited = all_rate_limited


class RepositoryWithoutValidBotError(Exception):
    pass
