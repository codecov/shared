import random
import requests
from ddt import data, ddt
from htmldom import htmldom

from tests import TornadoTestClass
from torngit.bitbucket import Bitbucket


@ddt
class Test(TornadoTestClass):
    @data(('codecov/private', None, 404, False),  # private guest
          ('codecov/private', 'testfxv0vfkohpqj5lruzp81y1f4868oo4a3', 200, True),  # private auth
          ('codecov/ci-repo', None, 200, False),  # public guest
          ('codecov/ci-repo', '5cccb375-a2d4-4a9c-89ac-0459bea2cb53', 200, False),  # public noauth
          ('codecov/ci-repo', '6ef29b63-1288-4ceb-8dfc-af2c03f5cd49', 200, True),  # public auth
          ('codecov-example-team/blank', None, 404, False),  # team private guest
          ('codecov-example-team/blank', '5cccb375-a2d4-4a9c-89ac-0459bea2cb53', 200, True),  # team private unauth
          ('codecov-example-team/blank', 'testfxv0vfkohpqj5lruzp81y1f4868oo4a3', 404, False),  # team private auth
          )
    def test_worthy(self, (repo, token, code, authorized)):
        if token:
            res = self.fetch('/bitbucket/%s?access_token=%s' % (repo, token))
        else:
            res = self.fetch('/bitbucket/'+repo)
        assert res.code == code
        assert ('<meta name="can_edit" value="%s">' % str(authorized).lower()) in res.body

    @data(('codecov-test', [{'repo': 'example-private', 'service_id': '6b8ce5c0-1a3d-4253-b761-f46a8046427d'}, {'repo': 'example-public', 'service_id': '7daf309c-4269-463a-9104-b9786a6b0a4e'}], 'testfxv0vfkohpqj5lruzp81y1f4868oo4a3'),
          ('codecov_io', [{'repo': 'example', 'service_id': 'e488381f-26a2-4466-9080-dd7acacb4892'}], '5cccb375-a2d4-4a9c-89ac-0459bea2cb53'),
          ('codecov-example-team', [{'repo': 'blank', 'service_id': '21cd46b1-a4aa-496d-8898-2306ca2f60b1'}], '5cccb375-a2d4-4a9c-89ac-0459bea2cb53'))
    def test_refresh(self, (user, repos, token)):
        self.db.query("TRUNCATE repos cascade;")
        res = self.fetch('/bitbucket/'+user+'?refresh=t&access_token='+token)
        assert res.code == 200
        rows = self.db.query("SELECT service_id, repo from repos;")
        self.assertItemsEqual(rows, repos)

    def test_bitbucket_file_404(self):
        self.skipTest("not supported yet")
        self.db.query("""UPDATE commits set report = '{"parser": {"method": "json", "version": "0.0.3"}, "coverage": 67, "files": {"home/apple/README.md": {"coverage": 67, "lines": [null, [[0,5,1], [5,7,0], [7,11,1]], 1, 0, true, 5, 6, 1, 1, null, 1], "totals": {"hit": 6, "missed": 1, "partial": 2, "lines": 9 } } }, "totals": {"files": 4, "hit": 6, "missed": 1, "partial": 2, "lines": 9 } }' where repoid='07cbb12d-00aa-4eff-bdd5-43f155a37f40';""")
        result = self.fetch('/bitbucket/codecov-test/example-public/home/apple/README.md')
        assert result.code == 302
        assert result.headers.get('Location').endswith('/bitbucket/codecov-test/example-public/README.md')

    def test_bitbucket_repo_moved(self):
        self.db.query("""UPDATE repos set repo='blah' where repoid=7;""")
        result = self.fetch('/bitbucket/codecov/blah/README.md?acess_token=testfxv0vfkohpqj5lruzp81y1f4868oo4a3', follow_redirects=False)
        assert result.code == 302
        assert '/bitbucket/codecov/ci-repo/README.md' in result.headers.get('Location')

    def test_get_open_prs(self):
        assert Bitbucket(None, 'codecov', 'coverage.py').get_open_prs() == []
        assert Bitbucket(None, 'codecov', 'ci-repo').get_open_prs() == [('#1', '666f423214c1')]

    def test_find_pull_request(self):
        assert Bitbucket(None, 'stevepeak', 'not-a-repo').find_pull_request('a' * 40, 'no-branch') is None

    def test_post_comment(self):
        assert Bitbucket(None, 'stevepeak', 'not-a-repo').post_comment(1, "Hello world") is None

    def test_edit_comment(self):
        assert Bitbucket(None, 'stevepeak', 'not-a-repo').edit_comment(1, 1, "Hello world") is None

    def test_edit_comment_works(self):
        token = self.db.get("SELECT oauth_token as key, oauth_secret as secret from owners where ownerid=7 limit 1")
        v = str(random.random())
        assert Bitbucket(None, 'codecov', 'ci-repo', token=token).edit_comment(1, 6907280, v) is True
        # get comment text
        # Bitbucket does not update the comment api propertly. So we need to extract html
        res = requests.get('https://bitbucket.org/codecov/ci-repo/pull-request/1/pr/diff')
        dom = htmldom.HtmlDom().createDom(res.text)
        assert dom.find('#comment-6907280').attr('data-content') == v

    def test_get_pull_request_fail(self):
        assert Bitbucket(None, 'stevepeak', 'not-a-repo').get_pull_request("1") is None

    def test_get_pull_request(self):
        assert Bitbucket(None, 'codecov', 'ci-repo').get_pull_request("1") == {'base': {'branch': u'master', 'commit': u'0028015f7fa2'}, 'head': {'branch': u'pr', 'commit': u'666f423214c1'}, 'number': '1', 'id': 1, 'open': True}

    def test_get_user_id_none(self):
        assert Bitbucket(None, 'codecov', 'ci-repo').get_user_id("jfoenvonwpqenbpwndbp") is None

    def test_get_user_id(self):
        assert Bitbucket(None, 'codecov', 'ci-repo').get_user_id("stevepeak") == 'test6y9pl15lzivhmkgsk67k10x53n04i85o'

    def test_get_commit(self):
        commit = Bitbucket(None, 'codecov', 'ci-repo').get_commit('0028015f7fa260f5fd68f78c0deffc15183d955e')
        assert commit == {'date': u'2014-10-19T14:32:33+00:00',
                          'author_login': u'stevepeak',
                          'author_name': u'stevepeak',
                          'author_email': u'steve@stevepeak.net',
                          'author_id': 'test6y9pl15lzivhmkgsk67k10x53n04i85o'}

    def test_get_commit_not_found(self):
        commit = Bitbucket(None, 'codecov', 'ci-repo').get_commit('none')
        assert commit is None

    def test_branches(self):
        branches = sorted(Bitbucket(None, 'codecov', 'ci-repo').get_branches())
        assert map(lambda a: a[0], branches) == ['master', 'pr']
