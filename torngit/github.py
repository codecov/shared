import re
import os
from tornado import gen
from tornado.auth import OAuth2Mixin
from tornado.httputil import url_concat
from tornado.escape import json_decode, json_encode
from tornado.httpclient import HTTPError as ClientError

from torngit.status import Status
from torngit.base import BaseHandler


is_merge_commit = re.compile(r'Merge \w{40} into \w{40}').match


class Github(BaseHandler, OAuth2Mixin):
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
                pr='%(username)s/%(repo)s/pull/%(pr)s',
                branch='%(username)s/%(repo)s/tree/%(branch)s',
                tree='%(username)s/%(repo)s/tree/%(commitid)s',
                src='%(username)s/%(repo)s/blob/%(commitid)s/%(path)s',
                author='%(username)s/%(repo)s/commits?author=%(author)s',)

    @gen.coroutine
    def api(self, method, url, body=None, headers=None, **args):
        _headers = {'Accept': 'application/json',
                    'User-Agent': os.getenv('USER_AGENT', 'Default'),
                    'Authorization': 'token ' + self.token['key']}
        _headers.update(headers or {})
        _log = None

        method = (method or 'GET').upper()

        if url[0] == '/':
            _log = dict(event='api',
                        endpoint=url,
                        method=method,
                        consumer=self.token['username'])
            url = self.api_url + url

        url = url_concat(url, args).replace(' ', '%20')

        # eta = time()
        t1, t2 = tuple(map(int, os.getenv('ASYNC_TIMEOUTS', '5,15').split(',')))
        try:
            res = yield self.fetch(url,
                                   method=method,
                                   body=json_encode(body) if body else None,
                                   headers=_headers,
                                   ca_certs=self.verify_ssl if type(self.verify_ssl) is not bool else None,
                                   validate_cert=self.verify_ssl if type(self.verify_ssl) is bool else None,
                                   connect_timeout=t1,
                                   request_timeout=t2)

        except ClientError as e:
            self.log(status=e.response.code,
                     body=e.response.body,
                     rlx=e.response.headers.get('X-RateLimit-Remaining'),
                     rly=e.response.headers.get('X-RateLimit-Limit'),
                     rlr=e.response.headers.get('X-RateLimit-Reset'),
                     **_log)
            raise

        else:
            self.log(status=res.code,
                     rlx=res.headers.get('X-RateLimit-Remaining'),
                     rly=res.headers.get('X-RateLimit-Limit'),
                     rlr=res.headers.get('X-RateLimit-Reset'),
                     **_log)

            if res.code == 204:
                raise gen.Return(None)

            elif res.headers.get('Content-Type')[:16] == 'application/json':
                raise gen.Return(json_decode(res.body))

            else:
                raise gen.Return(res.body)

    # Generic
    # -------
    @gen.coroutine
    def get_branches(self):
        # https://developer.github.com/v3/repos/#list-branches
        page = 0
        branches = []
        while True:
            page += 1
            res = yield self.api('get', '/repos/'+self.slug+'/branches', per_page=100, page=page)
            if len(res) == 0:
                break
            branches.extend([(b['name'], b['commit']['sha']) for b in res])
            if len(res) < 100:
                break
        raise gen.Return(branches)

    @gen.coroutine
    def get_authenticated_user(self):
        creds = self._oauth_consumer_token()
        session = yield self.api('get', self.service_url + '/login/oauth/access_token',
                                 code=self.get_argument('code'),
                                 client_id=creds['key'],
                                 client_secret=creds['secret'])

        if session.get('access_token'):
            # set current token
            self._token = dict(key=session['access_token'])

            user = yield self.api('get', '/user')
            user.update(session or {})

            raise gen.Return(user)

        else:
            raise gen.Return(None)

    @gen.coroutine
    def get_authenticated(self):
        """Returns (can_view, can_edit)"""
        # https://developer.github.com/v3/repos/#get
        r = yield self.api('get', '/repos/' + self.slug)
        ok = r['permissions']['admin'] or r['permissions']['push']
        raise gen.Return((True, ok))

    @gen.coroutine
    def get_repository(self):
        if self['repo_service_id'] is None:
            # https://developer.github.com/v3/repos/#get
            res = yield self.api('get', '/repos/' + self.slug)
        else:
            res = yield self.api('get', '/repositories/' + str(self['repo_service_id']))
        username, repo = tuple(res['full_name'].split('/', 1))
        raise gen.Return(dict(owner_service_id=res['owner']['id'], repo_service_id=res['id'],
                              private=res['private'], branch=res['default_branch'] or 'master',
                              username=username, repo=repo))

    # User Endpoints
    # --------------
    @gen.coroutine
    def list_repos(self, username=None):
        headers = {}
        if self.service == 'github_enterprise':
            headers['Accept'] = 'application/vnd.github.moondragon+json'
        page = 0
        data = []
        while True:
            page += 1
            # https://developer.github.com/v3/repos/#list-your-repositories
            repos = yield self.api('get', '/user/repos?per_page=100&page=%d' % page,
                                   headers=headers)

            for repo in repos:
                _o, _r, _p, parent = repo['owner']['login'], repo['name'], repo['private'], None
                if repo['fork']:
                    # need to get its source
                    # https://developer.github.com/v3/repos/#get
                    try:
                        parent = yield self.api('get', '/repos/'+_o+'/'+_r, headers=headers)
                        parent = parent['source']
                    except:
                        parent = None

                data.append(dict(repo_service_id=repo['id'], owner_service_id=repo['owner']['id'],
                                 username=_o, repo=_r,
                                 private=_p, branch=repo['default_branch'],
                                 fork=dict(repo_service_id=parent['id'], owner_service_id=parent['owner']['id'],
                                           username=parent['owner']['login'], repo=parent['name'],
                                           private=parent['private'], branch=parent['default_branch']) if parent else None))

            if len(repos) < 100:
                break

        raise gen.Return(data)

    @gen.coroutine
    def list_teams(self):
        # https://developer.github.com/v3/orgs/#list-your-organizations
        orgs = yield self.api('get', '/user/orgs')
        data = []
        # organization names
        for org in orgs:
            org = yield self.api('get', '/users/' + org['login'])
            data.append(dict(name=org['name'] or org['login'],
                             id=str(org['id']),
                             email=org['email'],
                             username=org['login']))

        raise gen.Return(data)

    # Commits
    # -------
    @gen.coroutine
    def get_commits(self, branch=None, pr=None):
        if pr:
            # https://developer.github.com/v3/pulls/#list-commits-on-a-pull-request
            # NOTE limited to 250 commits
            res = yield self.api('get', '/repos/' + self.slug + '/pulls/' + str(pr) + '/commits')
        else:
            # https://developer.github.com/v3/repos/commits/#list-commits-on-a-repository
            res = yield self.api('get', '/repos/' + self.slug + '/commits',
                                 sha=branch)

        raise gen.Return(map(lambda c: c['sha'], res))

    # Webhook
    # -------
    @gen.coroutine
    def create_hook(self, url, events, secret):
        # https://developer.github.com/v3/repos/hooks/#create-a-hook
        res = yield self.api('post', '/repos/' + self.slug + '/hooks',
                             body=dict(name='web', active=True, events=events,
                                       config=dict(url=url, secret=secret, content_type='json')))
        raise gen.Return(res['id'])

    # Comments
    # --------
    @gen.coroutine
    def post_comment(self, issueid, body):
        # https://developer.github.com/v3/issues/comments/#create-a-comment
        res = yield self.api('post', '/repos/'+self.slug+'/issues/'+str(issueid)+'/comments',
                             body=dict(body=body))
        raise gen.Return(res['id'])

    @gen.coroutine
    def edit_comment(self, issueid, commentid, body):
        # https://developer.github.com/v3/issues/comments/#edit-a-comment
        yield self.api('patch', '/repos/'+self.slug+'/issues/comments/'+str(commentid),
                       body=dict(body=body))
        raise gen.Return(True)

    # Commit Status
    # -------------
    @gen.coroutine
    def set_commit_status(self, commit, status, context, description, url=None, _merge=None):
        # https://developer.github.com/v3/repos/statuses
        assert status in ('pending', 'success', 'error', 'failure'), 'status not valid'
        yield self.api('post', '/repos/'+self.slug+'/statuses/'+commit,
                       body=dict(state=status,
                                 target_url=url,
                                 context=context,
                                 description=description))
        # check if the commit is a Merge
        if _merge is None:
            merge_commit = yield self._get_merge_commit_head(commit)
            if merge_commit:
                yield self.set_commit_status(merge_commit, status, context, description, url, True)
        raise gen.Return(True)

    @gen.coroutine
    def get_commit_statuses(self, commit, _merge=None):
        # https://developer.github.com/v3/repos/statuses/#list-statuses-for-a-specific-ref
        res = yield self.api('get', '/repos/'+self.slug+'/commits/'+commit+'/statuses')
        if len(res) == 0:
            if _merge is None:
                # check if its a merge commit
                merge_commit = yield self._get_merge_commit_head(commit)
                if merge_commit:
                    res = yield self.get_commit_statuses(merge_commit, True)
                    raise gen.Return(res)
            raise gen.Return(None)

        statuses = [{'time': s['updated_at'],
                     'state': s['state'],
                     'url': s['target_url'],
                     'context': s['context']} for s in res]
        raise gen.Return(Status(statuses))

    @gen.coroutine
    def get_commit_status(self, commit, _merge=None):
        # https://developer.github.com/v3/repos/statuses/#get-the-combined-status-for-a-specific-ref
        res = yield self.api('get', '/repos/'+self.slug+'/commits/'+commit+'/status')
        raise gen.Return(res['state'])

    # Source
    # ------
    @gen.coroutine
    def get_source(self, path, ref):
        # https://developer.github.com/v3/repos/contents/#get-contents
        content = yield self.api('get', '/repos/'+self.slug+'/contents/'+path,
                                 ref=ref, headers={"Accept": "application/vnd.github.v3.raw"})
        raise gen.Return(content)

    @gen.coroutine
    def get_diff(self, commit, commit2=None, context=True):
        if commit2:
            # https://developer.github.com/v3/repos/commits/#compare-two-commits
            res = yield self.api('get', '/repos/'+self.slug+'/compare/'+commit+'...'+commit2,
                                 headers={'Accept': 'application/vnd.github.v3.diff'})
            raise gen.Return(res)
        else:
            # https://developer.github.com/v3/repos/commits/#get-a-single-commit
            res = yield self.api('get', '/repos/'+self.slug+'/commits/'+commit,
                                 headers={'Accept': 'application/vnd.github.v3.diff'})
            raise gen.Return(res)

    @gen.coroutine
    def get_commit(self, commit):
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        res = yield self.api('get', '/repos/'+self.slug+'/commits/'+commit)
        raise gen.Return(dict(author_id=str(res['author']['id']) if res['author'] else None,
                              author_login=res['author']['login'] if res['author'] else None,
                              author_email=res['commit']['author'].get('email'),
                              author_name=res['commit']['author'].get('name'),
                              message=res['commit']['message'],
                              date=res['commit']['author'].get('date')))

    # Pull Requests
    # -------------
    @gen.coroutine
    def get_pull_request(self, pr):
        # https://developer.github.com/v3/pulls/#get-a-single-pull-request
        res = yield self.api('get', '/repos/'+self.slug+'/pulls/'+str(pr))
        raise gen.Return(dict(base=dict(branch=res['base']['ref'],
                                        commit=res['base']['sha']),
                              head=dict(branch=res['head']['ref'],
                                        commit=res['head']['sha']),
                              open=res['state'] == 'open',
                              merged=res['merged'],
                              id=str(pr), number=str(pr)))

    @gen.coroutine
    def get_pull_requests(self, commit=None, state='open', _was_merge_commit=False):
        if commit:
            # https://developer.github.com/v3/search/#search-issues
            prs = yield self.api('get', '/search/issues', q='%s+repo:%s' % (commit, self.slug))
            if prs['items']:
                raise gen.Return([str(pr['number']) for pr in prs['items'] if pr['state'] == state])

            elif not _was_merge_commit:
                merge_commit = yield self._get_merge_commit_head(commit)
                if merge_commit:
                    res = yield self.get_pull_requests(merge_commit, state=state, _was_merge_commit=True)
                    raise gen.Return(res)

            else:
                raise gen.Return([])

        else:
            # https://developer.github.com/v3/pulls/#list-pull-requests
            page = 0
            prs = []
            while True:
                page += 1
                res = yield self.api('get', '/repos/'+self.slug+'/pulls',
                                     state=state, per_page=100, page=page)
                if len(res) == 0:
                    break

                prs.extend([str(b['number']) for b in res if b['state'] == state])
                if len(res) < 100:
                    break

            raise gen.Return(prs)

    # Helpers
    # -------
    @gen.coroutine
    def _get_merge_commit_head(self, commit):
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        res = yield self.api('get', '/repos/'+self.slug+'/commits/'+commit)
        message = res.get('commit', {}).get('message', '')
        if is_merge_commit(message):
            raise gen.Return(message.split()[1])
