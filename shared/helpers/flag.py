from shared.helpers.yaml import walk


class Flag(object):
    def __init__(
        self, report, name, totals=None, carriedforward=False, carriedforward_from=None
    ):
        self._report = report
        self.name = name
        # TODO cache by storing in database
        self._totals = totals
        self.carriedforward = carriedforward
        self.carriedforward_from = carriedforward_from

    @property
    def report(self):
        """returns the report filtered by this flag
        """
        paths = walk(self._report.yaml, ("flags", self.name, "paths"))
        return self._report.filter(paths=paths, flags=[self.name])

    @property
    def totals(self):
        if not self._totals:
            with self.report as report:
                self._totals = report.totals
        return self._totals

    def apply_diff(self, diff):
        with self.report as report:
            return report.apply_diff(diff, _save=False)
