from covreports.helpers.Yaml import Yaml


class Flag(object):
    def __init__(self, report, name, totals=None):
        self._report = report
        self.name = name
        # TODO cache by storing in database
        self._totals = totals

    @property
    def report(self):
        """returns the report filtered by this flag
        """
        paths = Yaml.walk(self._report.yaml, ('flags', self.name, 'paths'))
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
