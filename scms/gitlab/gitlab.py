import os
import requests
from json import dumps
import urllib as urllib_parse
from collections import defaultdict

from app.services.service import ServiceBase, ServiceEngine, api


class GitlabBase(ServiceBase):
    service = 'gitlab'
    service_url = 'https://gitlab.com'
    icon = 'fa-git'
    verify_ssl = None
    urls = dict(owner='%(username)s',
                repo='%(username)s/%(repo)s',
                commit='%(username)s/%(repo)s/commit/%(commitid)s',
                commits='%(username)s/%(repo)s/commits',
                compare='%(username)s/%(repo)s/compare/%(base)s...%(head)s',
                blob='%(username)s/%(repo)s/blob/%(commitid)s/%(path)s',
                branch='%(username)s/%(repo)s/tree/%(branch)s',
                pr='%(username)s/%(repo)s/merge_requests/%(pr)s',
                tree='%(username)s/%(repo)s/tree/%(commitid)s')

    def diff_to_json(self, diff, report, context=True):
        for d in diff:
            mode = ''
            if d['deleted_file']:
                mode = 'deleted file mode\n'
            d['diff'] = ('diff --git a/%(old_path)s b/%(new_path)s\n' % d) + mode + d['diff']
        return super(GitlabBase, self).diff_to_json('\n'.join(map(lambda a: a['diff'], diff)), report, context)


class GitlabEngine(GitlabBase, ServiceEngine):
    @property
    def session(self):
        return dict(timeout=tuple(map(int, os.getenv('ASYNC_TIMEOUTS', '5,15').split(',', 1))),
                    verify=self.verify_ssl,
                    headers={"Accept": "application/json",
                             "User-Agent": "codecov.io",
                             "Authorization": "Bearer %s" % self.token['key']})

    @api
    def refresh(self, username, ownerid):
        repositories, page = defaultdict(list), 0
        while True:
            page += 1
            # http://doc.gitlab.com/ce/api/projects.html#projects
            res = requests.get(self.service_url + "/api/v3/projects?per_page=100&page=%d" % page, **self.session)
            res.raise_for_status()
            data = []
            repos = res.json()
            for repo in repos:
                owner = repo['namespace']
                _o, _r, _p = owner['path'], repo['path'], not repo['public']
                data.append(dict(repo_service_id=repo['id'], owner_service_id=owner['owner_id'] or owner['id'], fork=None,
                                 private=_p, branch=repo['default_branch'] or 'master', username=_o, repo=_r))
                if _p:
                    repositories[_o].append(_r)
            self.db.execute("SELECT refresh_repos('%s', '%s'::json);" % (self.service, dumps(data)))
            if len(repos) < 100:
                break

        cache = self.db.get("SELECT cache from owners where ownerid=%s limit 1", ownerid).cache or {}
        cache.update(repositories)
        # http://doc.gitlab.com/ce/api/groups.html#list-project-groups
        groups = requests.get(self.service_url + '/api/v3/groups', **self.session)
        self.db.execute("UPDATE owners set cache=%s, organizations=%s where ownerid=%s;", cache, [g['path'] for g in groups.json()], ownerid)

    @api
    def find_pull_request(self, commit, branch):
        # http://doc.gitlab.com/ce/api/merge_requests.html#list-merge-requests
        res = requests.get(self.service_url + "/api/v3/projects/%s/merge_requests?state=opened&order_by=updated_at" % self.repo_service_id, **self.session)
        res.raise_for_status()
        for _pr in res.json():
            if _pr['source_branch'] == branch:
                return dict(base=dict(branch=_pr['target_branch'],
                                      commit=self._get_head_of(_pr['target_branch'])),  # its only 12 long...ugh
                            head=dict(branch=_pr['source_branch'],
                                      commit=self._get_head_of(_pr['source_branch'])),
                            open=_pr['state'] == 'opened',
                            id=_pr['id'], number=_pr['iid'])

    @api
    def get_pull_request(self, pr):
        # http://doc.gitlab.com/ce/api/merge_requests.html
        res = requests.get(self.service_url + "/api/v3/projects/%s/merge_requests?iid=%s" % (self.repo_service_id, pr), **self.session)
        res.raise_for_status()
        for _pr in res.json():
            if str(_pr['iid']) == pr:
                return dict(base=dict(branch=_pr['target_branch'],
                                      commit=self._get_head_of(_pr['target_branch'])),  # its only 12 long...ugh
                            head=dict(branch=_pr['source_branch'],
                                      commit=self._get_head_of(_pr['source_branch'])),
                            open=_pr['state'] == 'opened',
                            id=_pr['iid'], number=pr)

    @api
    def _get_head_of(self, branch):
        # http://doc.gitlab.com/ce/api/branches.html#get-single-repository-branch
        res = requests.get(self.service_url + "/api/v3/projects/%s/repository/branches/%s" % (self.repo_service_id, branch), **self.session)
        res.raise_for_status()
        return res.json()['commit']['id']

    @api
    def post_comment(self, issueid, body):
        # http://doc.gitlab.com/ce/api/notes.html#create-new-merge-request-note
        res = requests.post(self.service_url + "/api/v3/projects/%s/merge_requests/%s/notes" % (self.repo_service_id, str(issueid)),
                            data=urllib_parse.urlencode(dict(body=body)), **self.session)
        res.raise_for_status()
        commentid = res.json()['id']
        return commentid

    @api
    def edit_comment(self, issueid, commentid, body):
        # http://doc.gitlab.com/ce/api/notes.html#modify-existing-merge-request-note
        res = requests.put(self.service_url + "/api/v3/projects/%s/merge_requests/%s/notes%s" % (self.repo_service_id, issueid, commentid),
                           data=urllib_parse.urlencode(dict(body=body)), **self.session)
        res.raise_for_status()
        return True

    @api
    def get_userid(self, login):
        # http://doc.gitlab.com/ee/api/users.html#list-users
        res = requests.get(self.service_url + "/api/v3/users?search=%s" % login, **self.session)
        res.raise_for_status()
        data = res.json()
        userid = (filter(lambda a: a['username'] == login, data) or [dict(id=None)])[0]['id']
        return userid

    @api
    def get_commit(self, commit):
        # http://doc.gitlab.com/ce/api/commits.html#get-a-single-commit
        res = requests.get(self.service_url + "/api/v3/projects/%s/repository/commits/%s" % (self.repo_service_id, commit), **self.session)
        res.raise_for_status()
        data = res.json()
        return dict(author_id=str(self.get_userid(data['author_name'])),
                    author_login=data['author_name'],
                    author_email=data['author_email'],
                    author_name=data['author_name'],
                    date=data['committed_date'])

    @api
    def get_branches(self):
        # http://doc.gitlab.com/ce/api/projects.html#list-branches
        res = requests.get(self.service_url + "/api/v3/projects/%s/repository/branches" % self.repo_service_id, **self.session)
        res.raise_for_status()
        return [(b['name'], b['commit']['id']) for b in res.json()]

    @api
    def get_open_prs(self):
        # http://doc.gitlab.com/ce/api/merge_requests.html#list-merge-requests
        res = requests.get(self.service_url + "/api/v3/projects/%s/merge_requests?state=opened" % self.repo_service_id, **self.session)
        res.raise_for_status()
        return [('#'+str(b['iid']), None) for b in res.json()]
