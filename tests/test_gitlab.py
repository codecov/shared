import subprocess
from ddt import data, ddt
from tests import TornadoTestClass

from app.services.gitlab.gitlab import GitlabEngine


@ddt
class Test(TornadoTestClass):
    def test_no_github(self):
        res = subprocess.check_output(
            'grep -R "github" app/services/gitlab/* || echo "ok"',
            shell=True).strip()
        assert res == 'ok'

    def test_file_structure(self):
        "files are all showing up, reporting accurate figures"
        response = self.fetch('/gitlab/codecov/ci-repo')
        assert response.code == 200
        self.assertExists('table.table>tbody>tr')
        assert response.dom.find('tbody>tr').first().find(
            'td').last().text().strip() == "54.55%"

    def test_file_ref(self):
        assert self.fetch(
            '/gitlab/codecov/ci-repo/README.md?ref=master').code == 200

    def test_not_a_user(self):
        response = self.fetch("/gitlab/not-a-real-user-with-repos?refresh=t")
        assert response.code == 200

    def test_no_repo(self):
        "404: repo does not exist"
        assert self.fetch('/gitlab/codecov/not-real').code == 404

    def test_ref_commit(self):
        "?ref=:commit"
        assert self.fetch(
            '/gitlab/codecov/ci-repo?ref=0028015f7fa260f5fd68f78c0deffc15183d955e'
        ).code == 200

    def test_new_repo(self):
        assert self.fetch('/gitlab/twbs/bootstrap').code == 404

    def test_get_open_prs(self):
        assert GitlabEngine('187725', 'codecov',
                            'ci-repo').get_open_prs() == [('#1', None)]

    def test_will_fetch_repo_logged_in(self):
        self.db.query("DELETE from repos cascade;")
        assert self.fetch(
            '/gitlab/codecov/ci-repo?access_token=testthtqqsfqxr2q1yyes8zzs4zndsu6nsb2'
        ).code == 200
        assert self.fetch(
            '/gitlab/codecov/ci-private?access_token=testthtqqsfqxr2q1yyes8zzs4zndsu6nsb2'
        ).code == 200

    def test_refresh(self):
        response = self.fetch(
            "/gitlab/codecov?refresh=t&access_token=testthtqqsfqxr2q1yyes8zzs4zndsu6nsb2"
        )
        assert response.code == 200
        repos = self.db.query(
            "SELECT branch, private, repo from repos where ownerid=10;")
        self.assertItemsEqual(repos, [{
            'branch': 'master',
            'private': False,
            'repo': 'ci-repo'
        }, {
            'branch': 'master',
            'private': True,
            'repo': 'ci-private'
        }])

    def test_is_member(self):
        ownerid = self.db.get(
            """INSERT INTO owners (service_id, service, username, oauth_token, oauth_secret) VALUES ('109479', 'gitlab', 'stevepeak', null, null) returning ownerid;"""
        ).ownerid
        token = self.db.get(
            "INSERT INTO sessions (ownerid, type) values (%s, 'login') returning sessionid;",
            ownerid).sessionid
        self.db.get(
            """INSERT INTO repos (service_id, ownerid, private, repo, upload_token, image_token, features) VALUES ('187440', %s, false, 'ci-repo', '58bbb451-1832-43ad-9d6b-6813f1386de3', '9903897381', null);""",
            ownerid)
        response = self.fetch("/gitlab/stevepeak/ci-repo?access_token=" +
                              token)
        assert response.code == 200
        token = self.db.get(
            "SELECT upload_token from repos where repo='ci-repo' and ownerid=(select ownerid from owners where service='gitlab' and username='stevepeak' limit 1);"
        ).upload_token
        assert token in response.body

    def test_is_member_group(self):
        res = self.fetch(
            "/gitlab/codecov-group?refresh=t&access_token=testthtqqsfqxr2q1yyes8zzs4zndsu6nsb2"
        )
        assert res.code == 200
        res = self.fetch(
            "/gitlab/codecov-group?access_token=testthtqqsfqxr2q1yyes8zzs4zndsu6nsb2"
        )
        assert res.code == 200
        assert '/gitlab/codecov-group/ci-repo' in res.body

    def test_is_not_member_public(self):
        ownerid = self.db.get(
            """INSERT INTO owners (service_id, service, username, organizations, oauth_token, oauth_secret) VALUES ('109479', 'gitlab', 'stevepeak', null, null, null) returning ownerid;"""
        ).ownerid
        token = self.db.get(
            "INSERT INTO sessions (ownerid, type) values (%s, 'login') returning sessionid;",
            ownerid).sessionid
        self.db.query(
            """INSERT INTO repos (service_id, ownerid, private, repo, upload_token, image_token, features) VALUES ('202581', %s, false, 'ci-repo-2', '58bbb451-1832-43ad-9d6b-6813f1386de3', '9903897381', null);""",
            ownerid)
        response = self.fetch("/gitlab/stevepeak/ci-repo-2?access_token=" +
                              token)
        assert response.code == 200

    def test_is_not_member_private(self):
        ownerid = self.db.get(
            """INSERT INTO owners (service_id, service, username, organizations, oauth_token, oauth_secret) VALUES ('109479', 'gitlab', 'stevepeak', null, null, null) returning ownerid;"""
        ).ownerid
        self.db.query(
            """INSERT INTO repos (service_id, ownerid, private, repo, upload_token, image_token, features) VALUES ('202581', %s, true, 'ci-repo-2', '58bbb451-1832-43ad-9d6b-6813f1386de3', '9903897381', null);""",
            ownerid)
        response = self.fetch(
            "/gitlab/stevepeak/ci-repo-2?access_token=testthtqqsfqxr2q1yyes8zzs4zndsu6nsb2"
        )
        assert response.code == 404

    def test_private(self):
        response = self.fetch(
            "/gitlab/codecov-group/ci-private?access_token=testthtqqsfqxr2q1yyes8zzs4zndsu6nsb2"
        )
        assert response.code == 200

    def test_file_not_exists(self):
        assert self.fetch(
            '/gitlab/codecov/ci-repo/other/file.md?ref=0028015f7fa260f5fd68f78c0deffc15183d955e'
        ).code == 404

    def test_find_pull_request(self):
        assert GitlabEngine(None, 'stevepeak', 'not-a-repo').find_pull_request(
            'a' * 40, 'no-branch') is None

    def test_post_comment(self):
        assert GitlabEngine(None, 'stevepeak', 'not-a-repo').post_comment(
            1, "Hello world") is None

    def test_edit_comment(self):
        assert GitlabEngine(None, 'stevepeak', 'not-a-repo').edit_comment(
            1, 1, "Hello world") is None

    def test_get_pull_request_fail(self):
        assert GitlabEngine(None, 'stevepeak',
                            'not-a-repo').get_pull_request("1") is None

    @data(('1', {
        'base': {
            'branch': u'master',
            'commit': '0028015f7fa260f5fd68f78c0deffc15183d955e'
        },
        'head': {
            'branch': u'other-branch',
            'commit': 'dd798926730aad14aadf72281204bdb85734fe67'
        },
        'number': '1',
        'id': 59639,
        'open': True
    }), ('100', None))
    def test_get_pull_request(self, (a, b)):
        assert GitlabEngine(
            '187725',
            'codecov',
            'ci-repo',
            token=dict(
                key=
                'testff3hzs8z959lb15xji4gudqt1ab2n3pnzgbnkxk9ie5ipg82ku2hmet78i5w'
            )).get_pull_request(a) == b

    def test_get_commit(self):
        commit = GitlabEngine(
            '187725', 'codecov',
            'ci-repo').get_commit('0028015f7fa260f5fd68f78c0deffc15183d955e')
        assert commit == {
            'date': '2014-10-19T14:32:33.000+00:00',
            'author_login': 'stevepeak',
            'author_name': 'stevepeak',
            'author_email': 'steve@stevepeak.net',
            'author_id': '109479'
        }

    def test_get_commit_not_found(self):
        commit = GitlabEngine('187725', 'codecov',
                              'ci-repo').get_commit('none')
        assert commit is None

    def test_branches(self):
        branches = sorted(
            GitlabEngine('187725', 'codecov', 'ci-repo').get_branches())
        assert map(lambda a: a[0], branches) == ['master', 'other-branch']
