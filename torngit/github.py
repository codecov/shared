import os
import socket
from time import time
from sys import stdout
from tornado import gen
from base64 import b64decode
from tornado.auth import OAuth2Mixin
from tornado.httputil import url_concat
from tornado.httpclient import HTTPError as ClientError
from tornado.escape import json_decode, json_encode, url_escape

from torngit.status import Status
from torngit.base import BaseHandler


class Github(BaseHandler, OAuth2Mixin):
    service = 'github'
    service_url = 'https://github.com'
    api_url = 'https://api.github.com'
    urls = dict(repo='%(username)s/%(name)s',
                owner='%(username)s',
                issues='%(username)s/%(name)s/issues/%(issueid)s',
                commit='%(username)s/%(name)s/commit/%(commitid)s',
                commits='%(username)s/%(name)s/commits',
                compare='%(username)s/%(name)s/compare/%(base)s...%(head)s',
                comment='%(username)s/%(name)s/issues/%(pullid)s#issuecomment-%(commentid)s',
                create_file='%(username)s/%(name)s/new/%(branch)s?filename=%(path)s&value=%(content)s',
                pull='%(username)s/%(name)s/pull/%(pullid)s',
                branch='%(username)s/%(name)s/tree/%(branch)s',
                tree='%(username)s/%(name)s/tree/%(commitid)s',
                src='%(username)s/%(name)s/blob/%(commitid)s/%(path)s',
                author='%(username)s/%(name)s/commits?author=%(author)s',)

    @gen.coroutine
    def api(self, method, url, body=None, headers=None, reraise=True, token=None, **args):
        _headers = {'Accept': 'application/json',
                    'User-Agent': os.getenv('USER_AGENT', 'Default')}

        if token or self.token:
            _headers['Authorization'] = 'token %s' % (token or self.token)['key']

        _headers.update(headers or {})
        _log = {}

        method = (method or 'GET').upper()

        if url[0] == '/':
            _log = dict(event='api',
                        endpoint=url,
                        method=method,
                        bot=(token or self.token).get('username'))
            url = self.api_url + url

        url = url_concat(url, args).replace(' ', '%20')

        kwargs = dict(method=method,
                      body=json_encode(body) if body else None,
                      headers=_headers,
                      ca_certs=self._verify_ssl if type(self._verify_ssl) is not bool else None,
                      validate_cert=self._verify_ssl if type(self._verify_ssl) is bool else None,
                      follow_redirects=False,
                      connect_timeout=self._timeouts[0],
                      request_timeout=self._timeouts[1])

        start = time()
        try:
            res = yield self.fetch(url, **kwargs)

        except ClientError as e:
            if e.response is None:
                stdout.write('count#%s.timeout=1\n' % self.service)
                raise ClientError(502, 'GitHub was not able to be reached, server timed out.')

            else:
                if e.response.code == 301:
                    # repo moved
                    self.data['repo']['service_id'] = e.response.effective_url.split('/')[4]
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

                if reraise:
                    error = ClientError(e.response.code, 'GitHub API: %s' % e.message)
                    if '"Bad credentials"' in e.response.body:
                        error.login = True
                    raise error

        except socket.gaierror:
            raise ClientError(502, 'GitHub was not able to be reached.')

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

        finally:
            stdout.write("source=%s measure#service=%dms\n" % (self.service, int((time() - start) * 1000)))

    # Generic
    # -------
    @gen.coroutine
    def get_branches(self, token=None):
        # https://developer.github.com/v3/repos/#list-branches
        page = 0
        branches = []
        while True:
            page += 1
            res = yield self.api('get', '/repos/%s/branches' % self.slug,
                                 per_page=100, page=page, token=token)
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
            self.set_token(dict(key=session['access_token']))

            user = yield self.api('get', '/user')
            user.update(session or {})

            raise gen.Return(user)

        else:
            raise gen.Return(None)

    @gen.coroutine
    def get_is_admin(self, user, token=None):
        # https://developer.github.com/v3/orgs/members/#get-organization-membership
        res = yield self.api('get', '/orgs/%s/memberships/%s' % (self.data['owner']['username'], user['username']), token=token)
        raise gen.Return(res['state'] == 'active' and res['role'] == 'admin')

    @gen.coroutine
    def get_authenticated(self, token=None):
        """Returns (can_view, can_edit)"""
        # https://developer.github.com/v3/repos/#get
        r = yield self.api('get', '/repos/%s' % self.slug, token=token)
        ok = r['permissions']['admin'] or r['permissions']['push']
        raise gen.Return((True, ok))

    @gen.coroutine
    def get_repository(self, token=None):
        if self.data['repo'].get('service_id') is None:
            # https://developer.github.com/v3/repos/#get
            res = yield self.api('get', '/repos/%s' % self.slug, token=token)
        else:
            res = yield self.api('get', '/repositories/%s' % self.data['repo']['service_id'], token=token)

        username, repo = tuple(res['full_name'].split('/', 1))
        parent = res.get('parent')

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

        raise gen.Return(dict(owner=dict(service_id=res['owner']['id'], username=username),
                              repo=dict(service_id=res['id'],
                                        name=repo,
                                        language=self._validate_language(res['language']),
                                        private=res['private'],
                                        fork=fork,
                                        branch=res['default_branch'] or 'master')))

    # User Endpoints
    # --------------
    @gen.coroutine
    def list_repos(self, username=None, token=None):
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
            if username is None:
                repos = yield self.api('get', '/user/repos?per_page=100&page=%d' % page,
                                       headers=headers, token=token)
            else:
                repos = yield self.api('get', '/users/%s/repos?per_page=100&page=%d' % (username, page),
                                       headers=headers, token=token)

            for repo in repos:
                _o, _r, parent = repo['owner']['login'], repo['name'], None
                if repo['fork']:
                    # need to get its source
                    # https://developer.github.com/v3/repos/#get
                    try:
                        parent = yield self.api('get', '/repos/%s/%s' % (_o, _r),
                                                headers=headers, token=token)
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
                                           private=repo['private'],
                                           branch=repo['default_branch'],
                                           fork=fork)))

            if len(repos) < 100:
                break

        raise gen.Return(data)

    @gen.coroutine
    def list_teams(self, token=None):
        # https://developer.github.com/v3/orgs/#list-your-organizations
        orgs = yield self.api('get', '/user/orgs', token=token)
        data = []
        # organization names
        for org in orgs:
            org = yield self.api('get', '/users/%s' % org['login'], token=token)
            data.append(dict(name=org['name'] or org['login'],
                             id=str(org['id']),
                             email=org['email'],
                             username=org['login']))

        raise gen.Return(data)

    # Commits
    # -------
    @gen.coroutine
    def get_pull_request_commits(self, pullid, token=None):
        # https://developer.github.com/v3/pulls/#list-commits-on-a-pull-request
        # NOTE limited to 250 commits
        res = yield self.api('get', '/repos/%s/pulls/%s/commits' % (self.slug, pullid), token=token)
        raise gen.Return([c['sha'] for c in res])

    # Webhook
    # -------
    @gen.coroutine
    def post_webhook(self, name, url, events, secret, token=None):
        # https://developer.github.com/v3/repos/hooks/#create-a-hook
        res = yield self.api('post', '/repos/%s/hooks' % self.slug,
                             body=dict(name='web', active=True, events=events,
                                       config=dict(url=url, secret=secret, content_type='json')),
                             token=token)
        raise gen.Return(res['id'])

    @gen.coroutine
    def edit_webhook(self, hookid, name, url, events, secret, token=None):
        # https://developer.github.com/v3/repos/hooks/#edit-a-hook
        yield self.api('patch', '/repos/%s/hooks/%s' % (self.slug, hookid),
                       body=dict(name='web', active=True, events=events,
                                 config=dict(url=url, secret=secret, content_type='json')),
                       token=token)
        raise gen.Return(True)

    @gen.coroutine
    def delete_webhook(self, hookid, token=None):
        # https://developer.github.com/v3/repos/hooks/#delete-a-hook
        yield self.api('delete', '/repos/%s/hooks/%s' % (self.slug, hookid), token=token)
        raise gen.Return(True)

    # Comments
    # --------
    @gen.coroutine
    def post_comment(self, issueid, body, token=None):
        # https://developer.github.com/v3/issues/comments/#create-a-comment
        res = yield self.api('post', '/repos/%s/issues/%s/comments' % (self.slug, issueid),
                             body=dict(body=body), token=token)
        raise gen.Return(res['id'])

    @gen.coroutine
    def edit_comment(self, issueid, commentid, body, token=None):
        # https://developer.github.com/v3/issues/comments/#edit-a-comment
        yield self.api('patch', '/repos/%s/issues/comments/%s' % (self.slug, commentid),
                       body=dict(body=body), token=token)
        raise gen.Return(True)

    @gen.coroutine
    def delete_comment(self, issueid, commentid, token=None):
        # https://developer.github.com/v3/issues/comments/#delete-a-comment
        yield self.api('delete', '/repos/%s/issues/comments/%s' % (self.slug, commentid), token=token)
        raise gen.Return(True)

    # Commit Status
    # -------------
    @gen.coroutine
    def set_commit_status(self, commit, status, context, description, url, token=None):
        # https://developer.github.com/v3/repos/statuses
        assert status in ('pending', 'success', 'error', 'failure'), 'status not valid'
        yield self.api('post', '/repos/%s/statuses/%s' % (self.slug, commit),
                       body=dict(state=status,
                                 target_url=url,
                                 context=context,
                                 description=description),
                       token=token)
        raise gen.Return(True)

    @gen.coroutine
    def get_commit_statuses(self, commit, token=None):
        # https://developer.github.com/v3/repos/statuses/#list-statuses-for-a-specific-ref
        res = yield self.api('get', '/repos/%s/commits/%s/statuses' % (self.slug, commit), token=token)
        if len(res) == 0:
            raise gen.Return(Status([]))

        statuses = [{'time': s['updated_at'],
                     'state': s['state'],
                     'url': s['target_url'],
                     'context': s['context']} for s in res]
        raise gen.Return(Status(statuses))

    @gen.coroutine
    def get_commit_status(self, commit, token=None):
        # https://developer.github.com/v3/repos/statuses/#get-the-combined-status-for-a-specific-ref
        res = yield self.api('get', '/repos/%s/commits/%s/status' % (self.slug, commit), token=token)
        raise gen.Return(res['state'])

    # Source
    # ------
    @gen.coroutine
    def get_source(self, path, ref, token=None):
        # https://developer.github.com/v3/repos/contents/#get-contents
        content = yield self.api('get', '/repos/%s/contents/%s' % (self.slug, path), ref=ref, token=token)
        raise gen.Return(dict(content=b64decode(content['content']), commitid=content['sha']))

    @gen.coroutine
    def get_commit_diff(self, commit, context=None, token=None):
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        res = yield self.api('get', '/repos/%s/commits/%s' % (self.slug, commit),
                             headers={'Accept': 'application/vnd.github.v3.diff'},
                             token=token)
        raise gen.Return(self.diff_to_json(res))

    @gen.coroutine
    def get_compare(self, base, head, context=None, with_commits=True, token=None):
        # https://developer.github.com/v3/repos/commits/#compare-two-commits
        res = yield self.api('get', '/repos/%s/compare/%s...%s' % (self.slug, base, head), token=token)
        files = {}
        for f in res['files']:
            diff = self.diff_to_json('diff --git a/%s b/%s%s\n%s\n%s\n%s' % (
                                     f.get('previous_filename') or f.get('filename'),
                                     f.get('filename'),
                                     '\ndeleted file mode 100644' if f['status'] == 'removed' else '\nnew file mode 100644' if f['status'] == 'added' else '',
                                     '--- ' + ('/dev/null' if f['status'] == 'new' else ('a/' + f.get('previous_filename', f.get('filename')))),
                                     '+++ ' + ('/dev/null' if f['status'] == 'removed' else ('b/' + f['filename'])),
                                     f.get('patch', '')))
            files.update(diff['files'])

        raise gen.Return(dict(diff=dict(files=files),
                              commits=[dict(commitid=c['sha'],
                                            message=c['commit']['message'],
                                            timestamp=c['commit']['author']['date'],
                                            author=dict(id=(c['author'] or {}).get('id'),
                                                        username=(c['author'] or {}).get('login'),
                                                        name=c['commit']['author']['name'],
                                                        email=c['commit']['author']['email'])) for c in ([res['base_commit']] + res['commits'])][::-1]))

    @gen.coroutine
    def get_commit(self, commit, token=None):
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        res = yield self.api('get', '/repos/%s/commits/%s' % (self.slug, commit), token=token)
        raise gen.Return(dict(author=dict(id=str(res['author']['id']) if res['author'] else None,
                                          username=res['author']['login'] if res['author'] else None,
                                          email=res['commit']['author'].get('email'),
                                          name=res['commit']['author'].get('name')),
                              commitid=commit,
                              parents=[p['sha'] for p in res['parents']],
                              message=res['commit']['message'],
                              timestamp=res['commit']['author'].get('date')))

    # Pull Requests
    # -------------
    @gen.coroutine
    def get_pull_request(self, pullid, token=None):
        # https://developer.github.com/v3/pulls/#get-a-single-pull-request
        res = yield self.api('get', '/repos/%s/pulls/%s' % (self.slug, pullid), token=token)
        raise gen.Return(dict(base=dict(branch=res['base']['ref'],
                                        commitid=res['base']['sha']),
                              head=dict(branch=res['head']['ref'],
                                        commitid=res['head']['sha']),
                              open=res['state'] == 'open',
                              merged=res['merged'],
                              title=res['title'],
                              id=str(pullid), number=str(pullid)))

    @gen.coroutine
    def get_pull_requests(self, commit=None, branch=None, state='open', token=None):
        query = '%srepo:%s+type:pr%s' % (
                (('%s+' % commit) if commit else ''),
                url_escape(self.slug),
                (('+state:%s' % state) if state else ''))

        # https://developer.github.com/v3/search/#search-issues
        prs = yield self.api('get', '/search/issues?q=%s' % query, token=token)
        if prs['items']:
            raise gen.Return([str(pr['number']) for pr in prs['items']])

        else:
            raise gen.Return([])
