import os
from json import loads
from json import dumps
from ddt import data, ddt
from tornado import template
from BeautifulSoup import BeautifulSoup as bs

from tests import TornadoTestClass
from app.helpers import get_start_of_line
from app.services.github.github import GithubEngine


@ddt
class Test(TornadoTestClass):
    repo = GithubEngine(None, 'codecov', 'ci-repo', commitid="abc123")

    def get_repo_url(self, *a, **k):
        return ''

    @data(("@@ -1 +1 @@", ('1', '', '1', '')),
          ("@@ -130,12 +142,15 @@ module.exports = (grunt) ->", ('130', '12', '142', '15')),
          ("@@ -0,0 +1,31 @@", ('0', '0', '1', '31')),
          ("@@ -325,44 +388,153 @@ window.Github = (function() {", ('325', '44', '388', '153')))
    def test_line_number(self, (diff, eq)):
        assert get_start_of_line(diff).groups() == eq

    @data(1, 2)
    def test_json(self, f):
        folder = 'tests/services/github/diff/'
        diff = self.readfile(folder + 'diff-%d.diff' % f)
        report = loads(self.readfile(folder + 'report-%d.json' % f))
        result = loads(self.readfile(folder + 'result-%d.json' % f))

        res = loads(dumps(self.repo.diff_to_json(diff, report)))
        print "\033[92m========== diff.json ===========\033[0m"
        print dumps(res)
        print "\033[92m========== end diff.json ===========\033[0m"
        assert res == result

        html = template.Loader(os.path.join(os.getcwd(), 'src/html/components')).load("diff.html").generate(handler=self, commitid='abc123', diff=res)
        html = bs(html).prettify().strip()
        print "\033[92m========== html ===========\033[0m"
        print html
        print "\033[92m========== end html ===========\033[0m"
        assert html == self.readfile(folder + 'html-%d.html' % f).strip()
