import re
import os
import requests
from json import dumps
from collections import defaultdict

from scms.scm import ServiceBase, ServiceEngine, api


is_merge_commit = re.compile(r'Merge \w{40} into \w{40}').match


class Github(ServiceBase):
    service = 'github'
    service_url = 'https://github.com'
    api_url = 'https://api.github.com'
    icon = 'fa-github'
    verify_ssl = None
    urls = dict(repo='%(username)s/%(repo)s',
                owner='%(username)s',
                commit='%(username)s/%(repo)s/commit/%(commitid)s',
                commits='%(username)s/%(repo)s/commits',
                compare='%(username)s/%(repo)s/compare/%(base)s...%(head)s',
                blob='%(username)s/%(repo)s/blob/%(commitid)s/%(path)s',
                pr='%(username)s/%(repo)s/pull/%(pr)s',
                branch='%(username)s/%(repo)s/tree/%(branch)s',
                tree='%(username)s/%(repo)s/tree/%(commitid)s')


class Github(ServiceEngine, Github):
    @property
    def headers(self):
        return dict(timeout=tuple(map(int, os.getenv('ASYNC_TIMEOUTS', '5,15').split(','))),
                    verify=self.verify_ssl,
                    headers={'Accept': 'application/json',
                             'User-Agent': 'Codecov',
                             'Authorization': 'token ' + self.token['key']})

    def handle_error(self, error):
        try:
            log = dict(ratelimit=error.headers.get("X-RateLimit-Remaining") + "/" + error.headers.get("X-RateLimit-Limit") + " " + error.headers.get("X-RateLimit-Reset"))
        except:
            log = {}

        return log

    @api
    def find_pull_request(self, commit, branch, _was_merge_commit=False):
        # https://developer.github.com/v3/search/#search-issues
        res = requests.get(self.api_url + "/search/issues?q=%s+is:open+repo:%s" % (commit, self.slug), **self.headers)
        res.raise_for_status()
        prs = res.json()
        if prs['items']:
            return self.get_pull_request(prs['items'][0]['number'])
        elif not _was_merge_commit:
            merge_commit_head = self.get_merge_commit_head(commit)
            if merge_commit_head:
                return self.find_pull_request(merge_commit_head, branch, True)

    def refresh(self, username, ownerid):
        headers = self.headers
        if self.service == 'github_enterprise':
            headers['headers']['Accept'] = 'application/vnd.github.moondragon+json'
        repositories, page = defaultdict(list), 0
        while True:
            page += 1
            # https://developer.github.com/v3/repos/#list-your-repositories
            res = requests.get(self.api_url + '/user/repos?per_page=100&page=%d' % page, **headers)
            data = []
            if res.status_code != 200:
                raise Exception("login")

            repos = res.json()
            for repo in repos:
                _o, _r, _p, parent = repo['owner']['login'], repo['name'], repo['private'], None
                if repo['fork'] and _p:
                    # need to get its source
                    # https://developer.github.com/v3/repos/#get
                    res = requests.get(self.api_url+'/repos/'+_o+'/'+_r, **headers)
                    parent = res.json()['source'] if res.status_code == 200 else None

                data.append(dict(repo_service_id=repo['id'], owner_service_id=repo['owner']['id'],
                                 username=_o, repo=_r,
                                 private=_p, branch=repo['default_branch'],
                                 fork=dict(repo_service_id=parent['id'], owner_service_id=parent['owner']['id'],
                                           username=parent['owner']['login'], repo=parent['name'],
                                           private=parent['private'], branch=parent['default_branch']) if parent else None))
                if _p:
                    repositories[_o].append(_r)
            self.db.execute("SELECT refresh_repos(%%s, '%s'::json);" % dumps(data), self.service)

            if len(repos) < 100:
                break

        # private repo cache
        cache = self.db.get("SELECT cache from owners where ownerid=%s limit 1", ownerid).cache or {}
        cache.update(repositories)
        # my organizations
        orgs = requests.get(self.api_url + '/user/orgs', **headers)
        if orgs.status_code == 200:
            orgs = orgs.json()
            self.db.execute("UPDATE owners set cache=%s, organizations=%s where ownerid=%s;", cache, [o['login'] for o in orgs], ownerid)
            # organization names
            for org in orgs:
                org = requests.get(self.api_url + '/users/%s' % org['login'], **headers)
                org = org.json()
                self.db.execute("UPDATE owners set name=%s, email=%s where service='github' and username=%s;",
                                org.get('name', org['login']), org.get('email'), org['login'])

    @api
    def get_pull_request(self, pr):
        # https://developer.github.com/v3/pulls/#get-a-single-pull-request
        res = requests.get(self.api_url + "/repos/%s/pulls/%s" % (self.slug, pr), **self.headers)
        res.raise_for_status()
        res = res.json()
        return dict(base=dict(branch=res['base']['ref'],
                              commit=res['base']['sha']),
                    head=dict(branch=res['head']['ref'],
                              commit=res['head']['sha']),
                    open=res['state'] == 'open',
                    id=pr, number=pr)

    @api
    def get_commits(self, branch=None, pr=None):
        if pr:
            # https://developer.github.com/v3/pulls/#list-commits-on-a-pull-request
            # NOTE limited to 250 commits
            res = requests.get(self.api_url + '/repos/' + self.slug + '/pulls/' + str(pr) + '/commits', **self.headers)
        else:
            # not used yet
            pass

        res.raise_for_status()
        return map(lambda c: c['sha'], res.json())

    @api
    def create_hook(self):
        # https://developer.github.com/v3/repos/hooks/#create-a-hook
        res = requests.post(self.api_url + "/repos/" + self.slug + "/hooks",
                            data=dumps(dict(name='web', active=True, events=['pull_request', 'delete', 'push', 'public'],
                                            config=dict(url=os.getenv('CODECOV_URL') + '/webhooks/' + self.service,
                                                        secret=os.getenv(self.service.upper() + '_WEBHOOK_SECRET'),
                                                        content_type='json'))), **self.headers)
        res.raise_for_status()
        return res.json()['id']

    @api
    def post_comment(self, issueid, body):
        # https://developer.github.com/v3/issues/comments/#create-a-comment
        res = requests.post(self.api_url + "/repos/%s/issues/%s/comments" % (self.slug, str(issueid)),
                            data=dumps(dict(body=body)), **self.headers)
        res.raise_for_status()
        commentid = res.json()['id']
        return commentid

    @api
    def edit_comment(self, issueid, commentid, body):
        # https://developer.github.com/v3/issues/comments/#edit-a-comment
        res = requests.patch(self.api_url + "/repos/%s/issues/comments/%s" % (self.slug, commentid),
                             data=dumps(dict(body=body)), **self.headers)
        res.raise_for_status()
        return True

    @api
    def post_status(self, commit, status, context, description, url=None, _merge=None):
        # https://developer.github.com/v3/repos/statuses
        assert status in ('pending', 'success', 'error', 'failure'), 'status not valid'
        res = requests.post(self.api_url + "/repos/%s/statuses/%s" % (self.slug, commit),
                            data=dumps(dict(state=status,
                                            target_url=url or self.get_repo_url(ref=_merge or commit),
                                            context=context,
                                            description=description)), **self.headers)
        res.raise_for_status()
        # check if the commit is a Merge
        if _merge is None:
            merge_commit_head = self.get_merge_commit_head(commit)
            if merge_commit_head:
                return self.post_status(merge_commit_head, status, context, description, url, commit)
        return res.json()

    @api
    def get_merge_commit_head(self, commit):
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        res = requests.get(self.api_url + "/repos/%s/commits/%s" % (self.slug, commit), **self.headers)
        res.raise_for_status()
        message = res.json().get('commit', {}).get('message', '')
        if is_merge_commit(message):
            return message.split()[1]

    @api
    def get_commit_status(self, commit, _merge=None):
        """
        Returns the communal status of the commit.
        """
        # https://developer.github.com/v3/repos/statuses/#list-statuses-for-a-specific-ref
        res = requests.get(self.api_url + "/repos/%s/commits/%s/statuses" % (self.slug, commit), **self.headers)
        res.raise_for_status()
        codecov_status = None
        github_statuses = res.json()
        states = dict(pending='pending', success='success', error='failure', failure='failure')
        statuses = tuple(map(lambda s: (s['context'], (s['updated_at'], s['state'])),
                             filter(self.is_ci_provider, github_statuses)))

        if len(statuses) == 0 and _merge is None:
            # check if its a merge commit
            merge_commit_head = self.get_merge_commit_head(commit)
            if merge_commit_head:
                return self.get_commit_status(merge_commit_head, True)

        codecov_status = max([(s['updated_at'], s['state'])
                              for s in github_statuses
                              if s['context'][:8] == 'codecov/'] or [(None, None)])[1]

        if len(github_statuses) == 0:
            # no github statuses at all... go ahead and send notifications based on average build len
            self.log(func="get_commit_status", commit=commit[:7], states="empty")
            return 'builds', codecov_status

        elif len(statuses) == 0:
            # no github statuses at all... go ahead and send notifications based on average build len
            self.log(func="get_commit_status", commit=commit[:7], states="unknown", contexts=",".join(set(map(lambda s: s['context'], github_statuses))))
            return 'builds', codecov_status

        by_ci = {}  # {"travis": [('today', 'success')]}
        [by_ci.setdefault(ci, []).append(state) for ci, state in statuses]
        # list of most recent states
        statuses = [states[max(_)[1]] for _ in by_ci.values()]

        self.log(func="get_commit_status", commit=commit[:7], states="%d/%d" % (statuses.count('success'), len(statuses)))

        if 'failure' in statuses:
            return 'failure', codecov_status
        elif 'success' in statuses:
            return 'success', codecov_status
        else:
            return 'pending', codecov_status

    @api
    def get_diff(self, commit, commit2=None, context=True):
        if commit2:
            # https://developer.github.com/v3/repos/commits/#compare-two-commits
            headers = self.headers
            headers['headers']['Accept'] = 'application/vnd.github.v3.diff'
            res = requests.get(self.api_url + "/repos/%s/compare/%s...%s" % (self.slug, commit, commit2), **headers)
            res.raise_for_status()
            return res.text
        else:
            # https://developer.github.com/v3/repos/commits/#get-a-single-commit
            headers = self.headers
            headers['headers']['Accept'] = 'application/vnd.github.v3.diff'
            res = requests.get(self.api_url + "/repos/%s/commits/%s" % (self.slug, commit), **headers)
            res.raise_for_status()
            return res.text

    @api
    def get_commit(self, commit):
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        res = requests.get(self.api_url + "/repos/%s/commits/%s" % (self.slug, commit), **self.headers)
        res.raise_for_status()
        data = res.json()
        return dict(author_id=str(data['author']['id']) if data['author'] else None,
                    author_login=data['author']['login'] if data['author'] else None,
                    author_email=data['commit']['author'].get('email'),
                    author_name=data['commit']['author'].get('name'),
                    date=data['commit']['author'].get('date'))

    @api
    def get_branches(self):
        # https://developer.github.com/v3/repos/#list-branches
        page = 0
        branches = []
        while True:
            page += 1
            res = requests.get(self.api_url + "/repos/%s/branches?per_page=100&page=%d" % (self.slug, page), **self.headers)
            res.raise_for_status()
            _branches = res.json()
            if len(_branches) == 0:
                break
            branches.extend([(b['name'], b['commit']['sha']) for b in _branches])
            if len(_branches) < 100:
                break
        return branches

    @api
    def get_open_prs(self):
        # https://developer.github.com/v3/pulls/#list-pull-requests
        page = 0
        prs = []
        while True:
            page += 1
            res = requests.get(self.api_url + "/repos/%s/pulls?state=open&per_page=100&page=%d" % (self.slug, page), **self.headers)
            res.raise_for_status()
            _prs = res.json()
            if len(_prs) == 0:
                break
            prs.extend([('#'+str(b['number']), b['head']['sha']) for b in _prs])
            if len(_prs) < 100:
                break
        return prs

    def is_ci_provider(self, status):
        if set((status['context'] or '').split('/')) & self.CI_CONTEXTS:
            return True
        elif set((status.get('target_url') or '').split('/')) & self.CI_PROVIDERS:
            return True
        return False
