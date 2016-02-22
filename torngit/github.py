import re
import os
from tornado import gen
from base64 import b64decode
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
    urls = dict(repo='%(username)s/%(name)s',
                owner='%(username)s',
                commit='%(username)s/%(name)s/commit/%(commitid)s',
                commits='%(username)s/%(name)s/commits',
                compare='%(username)s/%(name)s/compare/%(base)s...%(head)s',
                pull='%(username)s/%(name)s/pull/%(pr)s',
                branch='%(username)s/%(name)s/tree/%(branch)s',
                tree='%(username)s/%(name)s/tree/%(commitid)s',
                src='%(username)s/%(name)s/blob/%(commitid)s/%(path)s',
                author='%(username)s/%(name)s/commits?author=%(author)s',)

    @gen.coroutine
    def api(self, method, url, body=None, headers=None, reraise=True, **args):
        _headers = {'Accept': 'application/json',
                    'User-Agent': os.getenv('USER_AGENT', 'Default'),
                    'Authorization': 'token ' + self.token['key']}
        _headers.update(headers or {})
        _log = {}

        method = (method or 'GET').upper()

        if url[0] == '/':
            _log = dict(event='api',
                        endpoint=url,
                        method=method,
                        consumer=self.token.get('username'))
            url = self.api_url + url

        url = url_concat(url, args).replace(' ', '%20')

        try:
            res = yield self.fetch(url,
                                   method=method,
                                   body=json_encode(body) if body else None,
                                   headers=_headers,
                                   ca_certs=self.verify_ssl if type(self.verify_ssl) is not bool else None,
                                   validate_cert=self.verify_ssl if type(self.verify_ssl) is bool else None,
                                   follow_redirects=False,
                                   connect_timeout=self.timeouts[0],
                                   request_timeout=self.timeouts[1])

        except ClientError as e:
            if e.response.code == 301:
                # repo moved
                repo = yield self.get_repository()
                self.data['owner']['username'] = repo['owner']['username']
                self.data['repo']['name'] = repo['repo']['name']
                self.renamed_repository(repo)

            self.log(status=e.response.code,
                     body=e.response.body,
                     rlx=e.response.headers.get('X-RateLimit-Remaining'),
                     rly=e.response.headers.get('X-RateLimit-Limit'),
                     rlr=e.response.headers.get('X-RateLimit-Reset'),
                     **_log)

            if '"Bad credentials"' in e.response.body:
                e.message = 'login'

            if reraise:
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
    def get_is_admin(self, user):
        # https://developer.github.com/v3/orgs/members/#get-organization-membership
        res = yield self.api('get', '/orgs/'+self['owner']['username']+'/memberships/'+user['username'])
        raise gen.Return(res['state'] == 'active' and res['role'] == 'admin')

    @gen.coroutine
    def get_authenticated(self):
        """Returns (can_view, can_edit)"""
        # https://developer.github.com/v3/repos/#get
        r = yield self.api('get', '/repos/' + self.slug)
        ok = r['permissions']['admin'] or r['permissions']['push']
        raise gen.Return((True, ok))

    @gen.coroutine
    def get_repository(self):
        if self['repo'].get('service_id') is None:
            # https://developer.github.com/v3/repos/#get
            res = yield self.api('get', '/repos/' + self.slug)
        else:
            res = yield self.api('get', '/repositories/' + str(self['repo']['service_id']))

        username, repo = tuple(res['full_name'].split('/', 1))
        raise gen.Return(dict(owner=dict(service_id=res['owner']['id'], username=username),
                              repo=dict(service_id=res['id'],
                                        name=repo,
                                        private=res['private'],
                                        branch=res['default_branch'] or 'master')))

    # User Endpoints
    # --------------
    @gen.coroutine
    def list_repos(self):
        """
        GitHub includes all visible repos through
        the same endpoint.
        """
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

                if parent:
                    fork = dict(owner=dict(service_id=parent['owner']['id'],
                                           username=parent['owner']['login']),
                                repo=dict(service_id=parent['id'],
                                          name=parent['name'],
                                          language=self._validate_language(parent['language']),
                                          private=parent['private'],
                                          branch=parent['default_branch']))
                else:
                    fork = None

                data.append(dict(owner=dict(service_id=repo['owner']['id'],
                                            username=_o),
                                 repo=dict(service_id=repo['id'],
                                           name=_r,
                                           language=self._validate_language(repo['language']),
                                           private=_p,
                                           branch=repo['default_branch'],
                                           fork=fork)))

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
    def get_pull_request_commits(self, pullid):
        # https://developer.github.com/v3/pulls/#list-commits-on-a-pull-request
        # NOTE limited to 250 commits
        res = yield self.api('get', '/repos/' + self.slug + '/pulls/' + str(pullid) + '/commits')
        raise gen.Return([c['sha'] for c in res])

    # Webhook
    # -------
    @gen.coroutine
    def post_webhook(self, name, url, events, secret):
        # https://developer.github.com/v3/repos/hooks/#create-a-hook
        res = yield self.api('post', '/repos/' + self.slug + '/hooks',
                             body=dict(name='web', active=True, events=events,
                                       config=dict(url=url, secret=secret, content_type='json')))
        raise gen.Return(res['id'])

    @gen.coroutine
    def edit_webhook(self, hookid, name, url, events, secret):
        # https://developer.github.com/v3/repos/hooks/#edit-a-hook
        yield self.api('patch', '/repos/%s/hooks/%s' % (self.slug, hookid),
                       body=dict(name='web', active=True, events=events,
                                 config=dict(url=url, secret=secret, content_type='json')))
        raise gen.Return(True)

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

    @gen.coroutine
    def delete_comment(self, issueid, commentid):
        # https://developer.github.com/v3/issues/comments/#delete-a-comment
        yield self.api('delete', '/repos/'+self.slug+'/issues/comments/'+str(commentid))
        raise gen.Return(True)

    # Commit Status
    # -------------
    @gen.coroutine
    def set_commit_status(self, commit, status, context, description, url, _merge=None):
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
        content = yield self.api('get', '/repos/'+self.slug+'/contents/'+path, ref=ref)
        raise gen.Return(dict(content=b64decode(content['content']), commitid=content['sha']))

    @gen.coroutine
    def get_commit_diff(self, commit, context=None):
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        res = yield self.api('get', '/repos/'+self.slug+'/commits/'+commit,
                             headers={'Accept': 'application/vnd.github.v3.diff'})
        raise gen.Return(self.diff_to_json(res))

    @gen.coroutine
    def get_compare(self, base, head, context=None, with_commits=True):
        # https://developer.github.com/v3/repos/commits/#compare-two-commits
        res = yield self.api('get', '/repos/'+self.slug+'/compare/'+base+'...'+head)
        files = {}
        for f in res['files']:
            diff = self.diff_to_json('diff --git a/%s b/%s%s\n%s\n%s\n%s' % (
                                     f.get('previous_filename', f.get('filename')),
                                     f.get('filename'),
                                     '\ndeleted file mode 100644' if f['status'] == 'removed' else '\nnew file mode 100644' if f['status'] == 'added' else '',
                                     '--- ' + ('/dev/null' if f['status'] == 'new' else ('a/' + f.get('previous_filename', f.get('filename')))),
                                     '+++ ' + ('/dev/null' if f['status'] == 'removed' else ('b/' + f['filename'])),
                                     f.get('patch')))
            files.update(diff['files'])

        raise gen.Return(dict(diff=dict(files=files),
                              commits=[dict(commitid=c['sha'],
                                            message=c['commit']['message'],
                                            date=c['commit']['author']['date'],
                                            author=c['commit']['author']) for c in ([res['base_commit']] + res['commits'])]))

    @gen.coroutine
    def get_commit(self, commitid):
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        res = yield self.api('get', '/repos/'+self.slug+'/commits/'+commitid)
        raise gen.Return(dict(author=dict(id=str(res['author']['id']) if res['author'] else None,
                                          username=res['author']['login'] if res['author'] else None,
                                          email=res['commit']['author'].get('email'),
                                          name=res['commit']['author'].get('name')),
                              commitid=commitid,
                              parents=[p['sha'] for p in res['parents']],
                              message=res['commit']['message'],
                              date=res['commit']['author'].get('date')))

    # Pull Requests
    # -------------
    @gen.coroutine
    def get_pull_request(self, pr):
        # https://developer.github.com/v3/pulls/#get-a-single-pull-request
        res = yield self.api('get', '/repos/'+self.slug+'/pulls/'+str(pr))
        raise gen.Return(dict(base=dict(branch=res['base']['ref'],
                                        commitid=res['base']['sha']),
                              head=dict(branch=res['head']['ref'],
                                        commitid=res['head']['sha']),
                              open=res['state'] == 'open',
                              merged=res['merged'],
                              title=res['title'],
                              id=str(pr), number=str(pr)))

    @gen.coroutine
    def get_pull_requests(self, commitid=None, branch=None, state='open', _was_merge_commit=False):
        if commitid:
            # https://developer.github.com/v3/search/#search-issues
            prs = yield self.api('get', '/search/issues', q='%s+repo:%s' % (commitid, self.slug))
            if prs['items']:
                # [TODO] filter out branches
                raise gen.Return([str(pr['number']) for pr in prs['items'] if pr['state'] == state])

            elif not _was_merge_commit:
                merge_commit = yield self._get_merge_commit_head(commitid)
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

                prs.extend([str(b['number'])
                            for b in res
                            if b['state'] == state and
                               (branch is None or b['head']['ref'] == branch)])
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
