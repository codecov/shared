import os
from json import dumps
from json import loads
import oauth2 as oauth
from collections import defaultdict
from tornado.httputil import url_concat

from sign import signature
from app.tasks.reports.helpers import ratio, line_type
from app.services.service import ServiceBase, ServiceEngine, api


class BitbucketServerBase(ServiceBase):
    # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html
    service = 'bitbucket_server'
    service_url = os.getenv('BITBUCKET_SERVER_URL')
    api_url = os.getenv('BITBUCKET_SERVER_URL', '') + '/rest/api/1.0'
    icon = 'fa-bitbucket'
    urls = dict(owner='projects/%(username)s',
                repo='projects/%(username)s/repos/%(repo)s',
                commit='projects/%(username)s/repos/%(repo)s/commits/%(commitid)s',
                commits='projects/%(username)s/repos/%(repo)s/commits',
                blob='projects/%(username)s/repos/%(repo)s/browse/%(path)s?at=%(commitid)s',
                tree='projects/%(username)s/repos/%(repo)s/browse?at=%(commitid)s',
                branch='projects/%(username)s/repos/%(repo)s/browser?at=%(branch)s',
                pr='projects/%(username)s/repos/%(repo)s/pull-requests/%(pr)s/overview',
                compare='')

    if os.getenv('BITBUCKET_SERVER_VERIFY_SSL') == 'FALSE':
        # http://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification
        verify_ssl = dict(disable_ssl_certificate_validation=True)

    elif os.getenv('BITBUCKET_SERVER_SSL_PEM'):
        verify_ssl = dict(ca_certs=os.getenv('BITBUCKET_SERVER_SSL_PEM'))

    else:
        verify_ssl = dict(ca_certs=os.getenv('REQUESTS_CA_BUNDLE'))

    @property
    def project(self):
        """Stupid Bitbucket...
        Users repositories require a "~" before the username.
        This method will append that value accordingly
        """
        if str(self['owner_service_id'])[0] == 'U':
            return "~" + self['username'].upper()
        else:
            return self['username'].upper()

    def diff_to_json(self, diff_json, report, context=True):
        results = {}
        hits, misses, partials = [], [], []
        totals = [hits.append, misses.append, partials.append]

        for _diff in diff_json['diffs']:
            if not _diff['destination']:
                results[_diff['source']['toString']] = dict(type='deleted')

            else:
                fname = _diff['destination']['toString']
                cur_report = report['files'].get(fname)
                _before = _diff['source']['toString'] if _diff['source'] else None
                if not cur_report:
                    results[fname] = dict(type='empty')

                elif cur_report.get('ignored') is True:
                    results[fname] = dict(type='ignored',
                                          before=_before if _before != fname else None)

                else:
                    _file = results.setdefault(fname, dict(before=_before if _before != fname else None, segments=[],
                                                           type='new' if _before is None else 'modified'))

                    for hunk in _diff['hunks']:
                        segment = dict(header=[str(hunk['sourceLine']), str(hunk['sourceSpan']), str(hunk['destinationLine']), str(hunk['destinationSpan'])],
                                       lines=[])
                        _file['segments'].append(segment)
                        for seg in hunk['segments']:
                            if seg['type'] == 'CONTEXT' and not context:
                                # context lines, not edited
                                continue
                            _ = seg['type'][0]
                            for l in seg['lines']:
                                cov = cur_report['lines'].get(str(l['destination']))
                                _type = line_type(cov)
                                if _type < 3 and _ == 'A':
                                    totals[_type](1)
                                segment['lines'].append(dict(line=str(l['destination']),
                                                             type=('removed' if _ == 'R' else None if _ == 'C' else 'added'),
                                                             source=l['line'],
                                                             coverage=cov,
                                                             covered=['hit', 'miss', 'partial', None][_type],
                                                             message=(cur_report.get('messages') or {}).get(str(l['destination'])),
                                                             builds=[]))

        # create totals
        hits = sum(hits)
        misses = sum(misses)
        partials = sum(partials)
        lines = hits + misses + partials

        return dict(files=results,
                    totals=dict(hits=hits, misses=misses, partials=partials, lines=lines, coverage=ratio(hits, lines)))


class BitbucketServerEngine(BitbucketServerBase, ServiceEngine):
    def fetch(self, path=None, method="GET", body=None, url=None, **kwargs):
        # https://bitbucket.org/atlassian_tutorial/atlassian-oauth-examples/src/d625161454d1ca97b4515c6147b093fac9a68f7e/python/app.py?at=default&fileviewer=file-view-default
        consumer = oauth.Consumer(os.getenv('BITBUCKET_SERVER_CLIENT_ID'), '')
        token = oauth.Token(self.token['key'], self.token['secret'])
        client = oauth.Client(consumer, token, **self.verify_ssl)
        client.set_signature_method(signature)
        headers = {}
        if type(body) is dict:
            headers['Content-Type'] = 'application/json'
            body = dumps(body)

        url = (self.api_url + path) if not url else (os.getenv('BITBUCKET_SERVER_URL') + url)
        resp, content = client.request(url_concat(url, kwargs), method, body or '', headers)
        if resp.get('status') == '404':
            return None

        assert int(resp.get('status', 599)) < 400, content

        return loads(content) if content else None

    @api
    def find_pull_request(self, commit, branch):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2048016
        page = 0
        while True:
            page += 1
            res = self.fetch('/projects/%s/repos/%s/pull-requests' % (self.project, self.repo), page=page)
            for pr in res['values']:
                if pr['fromRef']['id'] == 'refs/heads/'+branch:
                    return dict(open=pr['open'], id=str(pr['id']), number=str(pr['id']),
                                base=dict(branch=pr['toRef']['id'].replace('refs/heads/', ''),
                                          commit=None),
                                head=dict(branch=pr['fromRef']['id'].replace('refs/heads/', ''),
                                          commit=None))

            if res['isLastPage']:
                break

    @api
    def get_pull_request(self, pr):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2167824
        res = self.fetch('/projects/%s/repos/%s/pull-requests/%s' % (self.project, self.repo, pr))
        if res:
            return dict(open=res['open'], id=str(pr), number=str(pr),
                        base=dict(branch=res['toRef']['id'].replace('refs/heads/', ''),
                                  commit=None),
                        head=dict(branch=res['fromRef']['id'].replace('refs/heads/', ''),
                                  commit=None))

    @api
    def refresh(self, _username, _ownerid):
        repositories, page = defaultdict(list), 0
        while True:
            page += 1
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2735328
            res = self.fetch('/repos')
            data = []
            for repo in res['values']:
                username, ownerid = repo['project']['key'].lower().replace('~', ''), repo['project']['id']
                slug, repoid, private = repo['slug'].lower(), repo['id'], (not repo.get('public', repo.get('origin', {}).get('public')))
                if repo['project']['type'] == 'PERSONAL':
                    ownerid = 'U%d' % repo['project']['owner']['id']

                data.append(dict(repo_service_id=repoid, owner_service_id=ownerid,
                                 username=username.lower(), repo=slug,
                                 private=private, branch='master',
                                 fork=None))
                if private:
                    repositories[username].append(slug)

            repositories.pop(_username, None)
            self.db.execute("SELECT refresh_repos('bitbucket_server', '%s'::json);" % dumps(data))
            if res['isLastPage']:
                break

        self.db.execute("UPDATE owners set cache=%s, organizations=%s where ownerid=%s;",
                        repositories, repositories.keys(), _ownerid)

    def get_merge_commit_head(self, commit):
        return None

    @api
    def get_commit_status(self, commit, _merge=None):
        """
        Returns the communal status of the commit.
        None: if any pending jobs or no jobs
        True: if all all successful
        False: if any single build failed
        builds: check if average number of builds is complete
        """
        # https://developer.atlassian.com/stash/docs/latest/how-tos/updating-build-status-for-commits.html
        page, statuses = 0, []
        all_statuses = []
        codecov_status = None
        while True:
            page += 1
            res = self.fetch(url='/rest/build-status/1.0/commits/' + commit, page=page)
            all_statuses.extend(res['values'])
            if res['isLastPage']:
                break

        statuses = map(lambda s: (s['key'], (s['dateAdded'], s['state'])),
                       filter(self.is_ci_provider, res['values']))

        codecov_status = max([(s['dateAdded'], s['state'])
                              for s in all_statuses
                              if s['name'][:8] == 'codecov/'] or [(None, None)])[1]

        states = dict(INPROGRESS='pending', SUCCESSFUL='success', FAILED='failure')
        statuses = set(statuses)

        if len(statuses) == 0:
            if _merge is None:
                # check if its a merge commit
                merge_commit_head = self.get_merge_commit_head(commit)
                if merge_commit_head:
                    return self.get_commit_status(merge_commit_head, True)

            self.log(func="get_commit_status", commit=commit[:7], states="empty")
            return 'builds', codecov_status

        by_ci = {}  # {"travis": [('today', 'success')]}
        [by_ci.setdefault(ci, []).append(state) for ci, state in statuses]
        # list of most recent states
        statuses = [states[max(_)[1]] for _ in by_ci.values()]

        self.log(func="get_commit_status", commit=commit[:7], states="%d/%d" % (statuses.count('success'), len(statuses)))

        if statuses:
            return 'failure', codecov_status
        elif 'success' in statuses:
            return 'success', codecov_status
        else:
            return 'pending', codecov_status

    def is_ci_provider(self, status):
        try:
            if set((status['key'] or '').split('/')) & self.CI_CONTEXTS:
                return True
            # This method may fail, but ignore and continue below
            return status['url'].split('/')[2] in self.CI_PROVIDERS
        except:
            pass

        return False

    @api
    def post_status(self, commit, status, context, description, url=None, _merge=None):
        # https://developer.atlassian.com/stash/docs/latest/how-tos/updating-build-status-for-commits.html
        assert status in ('pending', 'success', 'error', 'failure'), 'status not valid'
        res = self.fetch(url='/rest/build-status/1.0/commits/' + commit,
                         method='POST', body=dict(state=dict(pending='INPROGRESS', success='SUCCESSFUL', error='FAILED', failure='FAILED').get(status),
                                                  key=context,
                                                  name=context,
                                                  url=url or self.get_repo_url(ref=_merge or commit),
                                                  description=description))
        return res is None

    @api
    def post_comment(self, issueid, body):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3165808
        res = self.fetch('/projects/%s/repos/%s/pull-requests/%s/comments' % (self.project, self.repo, issueid),
                         method='POST', body=dict(text=body))
        return dict(id=str(res['id']), version=res['version'])

    @api
    def edit_comment(self, issueid, commentid, body, version):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3184624
        res = self.fetch('/projects/%s/repos/%s/pull-requests/%s/comments/%s' % (self.project, self.repo, str(issueid), str(commentid)),
                         method='PUT', body=dict(text=body, version=version))
        return dict(id=str(res['id']), version=res['version'])

    @api
    def get_user_id(self, login):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2649152
        res = self.fetch('/users/%s' % login)
        if res:
            return res['id']

    @api
    def get_commit(self, commit):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3530560
        res = self.fetch('/projects/%s/repos/%s/commits/%s' % (self.project, self.repo, str(commit)))
        if not res:
            return None
        author_name = res['author'].get('name')
        author_email = res['author'].get('emailAddress')
        # search by email or name
        author = self.find_user(author_name, author_email) or {}
        return dict(author_id=author.get('id'),
                    author_login=author.get('name'),
                    author_name=author_name,
                    author_email=author_email,
                    message=res['message'],
                    date=res['authorTimestamp'])

    @api
    def find_user(self, name, email):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2598928
        res = self.fetch('/users', filter=email)
        if not res['size']:
            res = self.fetch('/users', filter=name)
        return res['values'][0] if res['size'] else None

    @api
    def get_branches(self):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2243696
        branches, page = [], 0
        while True:
            page += 1
            res = self.fetch('/projects/%s/repos/%s/branches' % (self.project, self.repo), page=page)
            branches.extend([(b['displayId'], b['latestCommit']) for b in res['values']])
            if res['isLastPage']:
                break
        return branches

    @api
    def get_open_prs(self):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2048016
        prs, page = [], 0
        while True:
            page += 1
            res = self.fetch('/projects/%s/repos/%s/pull-requests' % (self.project, self.repo), page=page)
            prs.extend([('#'+str(b['id']), b['fromRef']['id'].replace('refs/heads/', '')) for b in res['values']])
            if res['isLastPage']:
                break
        return prs

    @api
    def get_diff(self, commit, commit2=None, context=True):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3358848
        res = self.fetch('/projects/%s/repos/%s/commits/%s/diff' % (self.project, self.repo, commit2 or commit),
                         contextLines=3 if context else 0,
                         withComments=False,
                         whitespace='ignore-all',
                         since=commit if commit2 else None)
        return res
