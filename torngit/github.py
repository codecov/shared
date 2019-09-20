import os
import socket
from time import time
from base64 import b64decode
import logging

from tornado.auth import OAuth2Mixin
from tornado.httputil import url_concat
from tornado.httpclient import HTTPError as ClientError
from tornado.escape import json_decode, json_encode, url_escape

from torngit.status import Status
from torngit.base import BaseHandler
from torngit.exceptions import (
    TorngitObjectNotFoundError, TorngitServerUnreachableError, TorngitServer5xxCodeError,
    TorngitClientError
)

log = logging.getLogger(__name__)


class Github(BaseHandler, OAuth2Mixin):
    service = 'github'
    service_url = 'https://github.com'
    api_url = 'https://api.github.com'
    urls = dict(
        repo='%(username)s/%(name)s',
        owner='%(username)s',
        user='%(username)s',
        issues='%(username)s/%(name)s/issues/%(issueid)s',
        commit='%(username)s/%(name)s/commit/%(commitid)s',
        commits='%(username)s/%(name)s/commits',
        compare='%(username)s/%(name)s/compare/%(base)s...%(head)s',
        comment=
        '%(username)s/%(name)s/issues/%(pullid)s#issuecomment-%(commentid)s',
        create_file=
        '%(username)s/%(name)s/new/%(branch)s?filename=%(path)s&value=%(content)s',
        pull='%(username)s/%(name)s/pull/%(pullid)s',
        branch='%(username)s/%(name)s/tree/%(branch)s',
        tree='%(username)s/%(name)s/tree/%(commitid)s',
        src='%(username)s/%(name)s/blob/%(commitid)s/%(path)s',
        author='%(username)s/%(name)s/commits?author=%(author)s',
    )

    async def api(self,
                  method,
                  url,
                  body=None,
                  headers=None,
                  token=None,
                  **args):
        _headers = {
            'Accept': 'application/json',
            'User-Agent': os.getenv('USER_AGENT', 'Default')
        }

        if token or self.token:
            _headers['Authorization'] = 'token %s' % (token
                                                      or self.token)['key']

        _headers.update(headers or {})
        log_dict = {}

        method = (method or 'GET').upper()

        if url[0] == '/':
            log_dict = dict(
                event='api',
                endpoint=url,
                method=method,
                bot=(token or self.token).get('username'))
            url = self.api_url + url

        url = url_concat(url, args).replace(' ', '%20')

        kwargs = dict(
            method=method,
            body=json_encode(body) if body else None,
            headers=_headers,
            ca_certs=self.verify_ssl
            if type(self.verify_ssl) is not bool else None,
            validate_cert=self.verify_ssl
            if type(self.verify_ssl) is bool else None,
            follow_redirects=False,
            connect_timeout=self._timeouts[0],
            request_timeout=self._timeouts[1])

        start = time()
        try:
            res = await self.fetch(url, **kwargs)

        except ClientError as e:
            if e.code == 599:
                log.info('count#%s.timeout=1\n' % self.service)
                raise TorngitServerUnreachableError('Github was not able to be reached, server timed out.')
            elif e.code >= 500:
                raise TorngitServer5xxCodeError("Github is having 5xx issues")
            log.warning(
                'Github HTTP %s' % e.response.code,
                extra=dict(
                    url=url,
                    body=e.response.body,
                    rlx=e.response.headers.get('X-RateLimit-Remaining'),
                    rly=e.response.headers.get('X-RateLimit-Limit'),
                    rlr=e.response.headers.get('X-RateLimit-Reset'),
                    **log_dict
                )
            )
            message = f'Github API: {e.message}'
            raise TorngitClientError(e.code, e.response, message)

        except socket.gaierror:
            raise TorngitServerUnreachableError('GitHub was not able to be reached.')

        else:
            log.info(
                'GitHub HTTP %s' % res.code,
                extra=dict(
                    rlx=res.headers.get('X-RateLimit-Remaining'),
                    rly=res.headers.get('X-RateLimit-Limit'),
                    rlr=res.headers.get('X-RateLimit-Reset'),
                    **log_dict
                )
            )
            if res.code == 204:
                return None

            elif res.headers.get('Content-Type')[:16] == 'application/json':
                return json_decode(res.body)

            else:
                return res.body

        finally:
            log.debug("source=%s measure#service=%dms\n" %
                         (self.service, int((time() - start) * 1000)))

    # Generic
    # -------
    async def get_branches(self, token=None):
        # https://developer.github.com/v3/repos/#list-branches
        page = 0
        branches = []
        while True:
            page += 1
            res = await self.api(
                'get',
                '/repos/%s/branches' % self.slug,
                per_page=100,
                page=page,
                token=token)
            if len(res) == 0:
                break
            branches.extend([(b['name'], b['commit']['sha']) for b in res])
            if len(res) < 100:
                break
        return branches

    async def get_authenticated_user(self):
        creds = self._oauth_consumer_token()
        session = await self.api(
            'get',
            self.service_url + '/login/oauth/access_token',
            code=self.get_argument('code'),
            client_id=creds['key'],
            client_secret=creds['secret'])

        if session.get('access_token'):
            # set current token
            self.set_token(dict(key=session['access_token']))

            user = await self.api('get', '/user')
            user.update(session or {})

            return user

        else:
            return None

    async def get_is_admin(self, user, token=None):
        # https://developer.github.com/v3/orgs/members/#get-organization-membership
        res = await self.api(
            'get',
            '/orgs/%s/memberships/%s' % (self.data['owner']['username'],
                                         user['username']),
            token=token)
        return res['state'] == 'active' and res['role'] == 'admin'

    async def get_authenticated(self, token=None):
        """Returns (can_view, can_edit)"""
        # https://developer.github.com/v3/repos/#get
        r = await self.api('get', '/repos/%s' % self.slug, token=token)
        ok = r['permissions']['admin'] or r['permissions']['push']
        return (True, ok)

    async def get_repository(self, token=None, _in_loop=None):
        if self.data['repo'].get('service_id') is None:
            # https://developer.github.com/v3/repos/#get
            res = await self.api('get', '/repos/%s' % self.slug, token=token)
        else:
            res = await self.api(
                'get',
                '/repositories/%s' % self.data['repo']['service_id'],
                token=token)

        username, repo = tuple(res['full_name'].split('/', 1))
        parent = res.get('parent')

        if parent:
            fork = dict(
                owner=dict(
                    service_id=parent['owner']['id'],
                    username=parent['owner']['login']),
                repo=dict(
                    service_id=parent['id'],
                    name=parent['name'],
                    language=self._validate_language(parent['language']),
                    private=parent['private'],
                    branch=parent['default_branch']
                )
            )
        else:
            fork = None

        return dict(
            owner=dict(
                service_id=res['owner']['id'],
                username=username
            ),
            repo=dict(
                service_id=res['id'],
                name=repo,
                language=self._validate_language(res['language']),
                private=res['private'],
                fork=fork,
                branch=res['default_branch'] or 'master'
            )
        )

    async def list_repos_using_installation(self, username):
        """
        returns list of service_id's of repos included in this integration
        """
        repos = []
        page = 0
        while True:
            page += 1
            # https://developer.github.com/v3/repos/#list-your-repositories
            res = await self.api(
                'get',
                '/installation/repositories?per_page=100&page=%d' % page,
                headers={
                    'Accept': 'application/vnd.github.machine-man-preview+json'
                })
            if len(res['repositories']) == 0:
                break
            repos.extend([repo['id'] for repo in res['repositories']])
            if len(res['repositories']) <= 100:
                break

        return repos

    async def list_repos(self, username=None, token=None):
        """
        GitHub includes all visible repos through
        the same endpoint.
        """
        page = 0
        data = []
        while True:
            page += 1
            # https://developer.github.com/v3/repos/#list-your-repositories
            if username is None:
                repos = await self.api(
                    'get',
                    '/user/repos?per_page=100&page=%d' % page,
                    token=token)
            else:
                repos = await self.api(
                    'get',
                    '/users/%s/repos?per_page=100&page=%d' % (username, page),
                    token=token)

            for repo in repos:
                _o, _r, parent = repo['owner']['login'], repo['name'], None
                if repo['fork']:
                    # need to get its source
                    # https://developer.github.com/v3/repos/#get
                    try:
                        parent = await self.api(
                            'get', '/repos/%s/%s' % (_o, _r), token=token)
                        parent = parent['source']
                    except Exception:
                        parent = None

                if parent:
                    fork = dict(
                        owner=dict(
                            service_id=parent['owner']['id'],
                            username=parent['owner']['login']),
                        repo=dict(
                            service_id=parent['id'],
                            name=parent['name'],
                            language=self._validate_language(
                                parent['language']),
                            private=parent['private'],
                            branch=parent['default_branch']))
                else:
                    fork = None

                data.append(
                    dict(
                        owner=dict(
                            service_id=repo['owner']['id'], username=_o),
                        repo=dict(
                            service_id=repo['id'],
                            name=_r,
                            language=self._validate_language(repo['language']),
                            private=repo['private'],
                            branch=repo['default_branch'],
                            fork=fork)))

            if len(repos) < 100:
                break

        return data

    async def list_teams(self, token=None):
        # https://developer.github.com/v3/orgs/#list-your-organizations
        page, data = 0, []
        while True:
            page += 1
            orgs = await self.api('get', '/user/orgs', page=page, token=token)
            if len(orgs) == 0:
                break
            # organization names
            for org in orgs:
                org = await self.api(
                    'get', '/users/%s' % org['login'], token=token)
                data.append(
                    dict(
                        name=org['name'] or org['login'],
                        id=str(org['id']),
                        email=org['email'],
                        username=org['login']))
            if len(orgs) < 30:
                break

        return data

    # Commits
    # -------
    async def get_pull_request_commits(self, pullid, token=None):
        # https://developer.github.com/v3/pulls/#list-commits-on-a-pull-request
        # NOTE limited to 250 commits
        res = await self.api(
            'get',
            '/repos/%s/pulls/%s/commits' % (self.slug, pullid),
            token=token)
        return [c['sha'] for c in res]

    # Webhook
    # -------
    async def post_webhook(self, name, url, events, secret, token=None):
        # https://developer.github.com/v3/repos/hooks/#create-a-hook
        res = await self.api(
            'post',
            '/repos/%s/hooks' % self.slug,
            body=dict(
                name='web',
                active=True,
                events=events,
                config=dict(url=url, secret=secret, content_type='json')),
            token=token)
        return res

    async def edit_webhook(self, hookid, name, url, events, secret,
                           token=None):
        # https://developer.github.com/v3/repos/hooks/#edit-a-hook
        try:
            return await self.api(
                'patch',
                '/repos/%s/hooks/%s' % (self.slug, hookid),
                body=dict(
                    name='web',
                    active=True,
                    events=events,
                    config=dict(url=url, secret=secret, content_type='json')),
                token=token)
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(ce.response, f"Cannot find webhook {hookid}")
            raise

    async def delete_webhook(self, hookid, token=None):
        # https://developer.github.com/v3/repos/hooks/#delete-a-hook
        try:    
            await self.api(
                'delete', '/repos/%s/hooks/%s' % (self.slug, hookid), token=token)
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(ce.response, f"Cannot find webhook {hookid}")
            raise
        return True

    # Comments
    # --------
    async def post_comment(self, issueid, body, token=None):
        # https://developer.github.com/v3/issues/comments/#create-a-comment
        res = await self.api(
            'post',
            '/repos/%s/issues/%s/comments' % (self.slug, issueid),
            body=dict(body=body),
            token=token)
        return res

    async def edit_comment(self, issueid, commentid, body, token=None):
        # https://developer.github.com/v3/issues/comments/#edit-a-comment
        try:
            return await self.api(
                'patch',
                '/repos/%s/issues/comments/%s' % (self.slug, commentid),
                body=dict(body=body),
                token=token)
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(ce.response, f"Cannot find comment {commentid} from PR {issueid}")
            raise

    async def delete_comment(self, issueid, commentid, token=None):
        # https://developer.github.com/v3/issues/comments/#delete-a-comment
        try:
            await self.api(
                'delete',
                '/repos/%s/issues/comments/%s' % (self.slug, commentid),
                token=token)
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(ce.response, f"Cannot find comment {commentid} from PR {issueid}")
            raise
        return True

    # Commit Status
    # -------------
    async def set_commit_status(self,
                                commit,
                                status,
                                context,
                                description,
                                url,
                                merge_commit=None,
                                token=None,
                                coverage=None):
        # https://developer.github.com/v3/repos/statuses
        assert status in ('pending', 'success', 'error',
                          'failure'), 'status not valid'
        try:
            res = await self.api(
                'post',
                '/repos/%s/statuses/%s' % (self.slug, commit),
                body=dict(
                    state=status,
                    target_url=url,
                    context=context,
                    description=description),
                token=token)
        except TorngitClientError as ce:
            raise
        if merge_commit:
            await self.api(
                'post',
                '/repos/%s/statuses/%s' % (self.slug, merge_commit[0]),
                body=dict(
                    state=status,
                    target_url=url,
                    context=merge_commit[1],
                    description=description),
                token=token)
        return res

    async def get_commit_statuses(self, commit, token=None):
        page = 0
        statuses = []
        while True:
            page += 1
            # https://developer.github.com/v3/repos/statuses/#list-statuses-for-a-specific-ref
            res = await self.api(
                'get',
                '/repos/%s/commits/%s/statuses' % (self.slug, commit),
                page=page,
                per_page=100,
                token=token)
            if len(res) == 0:
                break

            statuses.extend([{
                'time': s['updated_at'],
                'state': s['state'],
                'description': s['description'],
                'url': s['target_url'],
                'context': s['context']
            } for s in res])
            if len(res) < 100:
                break

        return Status(statuses)

    async def get_commit_status(self, commit, token=None):
        # https://developer.github.com/v3/repos/statuses/#get-the-combined-status-for-a-specific-ref
        res = await self.api(
            'get',
            '/repos/%s/commits/%s/status' % (self.slug, commit),
            token=token)
        return res['state']

    # Source
    # ------
    async def get_source(self, path, ref, token=None):
        # https://developer.github.com/v3/repos/contents/#get-contents
        try:
            content = await self.api(
                'get',
                '/repos/{0}/contents/{1}'.format(self.slug, path.replace(
                    ' ', '%20')),
                ref=ref,
                token=token)
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(ce.response, f"Path {path} not found at {ref}")
            raise
        return dict(
            content=b64decode(content['content']),
            commitid=content['sha']
        )

    async def get_commit_diff(self, commit, context=None, token=None):
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        try:
            res = await self.api(
                'get',
                '/repos/%s/commits/%s' % (self.slug, commit),
                headers={'Accept': 'application/vnd.github.v3.diff'},
                token=token)
        except TorngitClientError as ce:
            if ce.code == 422:
                raise TorngitObjectNotFoundError(ce.response, f"Commit with id {commit} does not exist")
            raise
        return self.diff_to_json(res.decode('utf-8'))

    async def get_compare(self,
                          base,
                          head,
                          context=None,
                          with_commits=True,
                          token=None):
        # https://developer.github.com/v3/repos/commits/#compare-two-commits
        res = await self.api(
            'get',
            '/repos/%s/compare/%s...%s' % (self.slug, base, head),
            token=token)
        files = {}
        for f in res['files']:
            diff = self.diff_to_json(
                'diff --git a/%s b/%s%s\n%s\n%s\n%s' %
                (f.get('previous_filename') or f.get('filename'),
                 f.get('filename'), '\ndeleted file mode 100644'
                 if f['status'] == 'removed' else '\nnew file mode 100644'
                 if f['status'] == 'added' else '', '--- ' +
                 ('/dev/null' if f['status'] == 'new' else
                  ('a/' + f.get('previous_filename', f.get('filename')))),
                 '+++ ' + ('/dev/null' if f['status'] == 'removed' else
                           ('b/' + f['filename'])), f.get('patch', '')))
            files.update(diff['files'])

        # commits are returned in reverse chronological order. ie [newest...oldest]
        return dict(
            diff=dict(
                files=files
            ),
            commits=[
                dict(
                    commitid=c['sha'],
                    message=c['commit']['message'],
                    timestamp=c['commit']['author']['date'],
                    author=dict(
                        id=(c['author'] or {}).get('id'),
                        username=(c['author'] or {}).get('login'),
                        name=c['commit']['author']['name'],
                        email=c['commit']['author']['email']))
                for c in ([res['base_commit']] + res['commits'])
            ][::-1]
        )

    async def get_commit(self, commit, token=None):
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        try:
            res = await self.api(
                'get', '/repos/%s/commits/%s' % (self.slug, commit), token=token)
        except TorngitClientError as ce:
            if ce.code == 422:
                raise TorngitObjectNotFoundError(ce.response, f"Commit with id {commit} does not exist")
            raise
        return dict(
            author=dict(
                id=str(res['author']['id']) if res['author'] else None,
                username=res['author']['login'] if res['author'] else None,
                email=res['commit']['author'].get('email'),
                name=res['commit']['author'].get('name')
            ),
            commitid=commit,
            parents=[p['sha'] for p in res['parents']],
            message=res['commit']['message'],
            timestamp=res['commit']['author'].get('date'))

    # Pull Requests
    # -------------
    def _pull(self, pull):
        return dict(
            base=dict(
                branch=pull['base']['ref'],
                commitid=pull['base']['sha']),
            head=dict(
                branch=pull['head']['ref'],
                commitid=pull['head']['sha']),
            state='merged' if pull['merged'] else pull['state'],
            title=pull['title'],
            id=str(pull['number']),
            number=str(pull['number']))

    async def get_pull_request(self, pullid, token=None):
        # https://developer.github.com/v3/pulls/#get-a-single-pull-request
        try:
            res = await self.api(
                'get', '/repos/%s/pulls/%s' % (self.slug, pullid), token=token)
        except TorngitClientError as ce:
            if ce.code == 404:
                raise TorngitObjectNotFoundError(ce.response, f"Pull Request {pullid} not found")
            raise
        return self._pull(res)

    async def get_pull_requests(self, state='open', token=None):
        # https://developer.github.com/v3/pulls/#list-pull-requests
        page, pulls = 0, []
        while True:
            page += 1
            res = await self.api(
                'get',
                '/repos/%s/pulls' % self.slug,
                page=page,
                per_page=25,
                state=state,
                token=token)
            if len(res) == 0:
                break

            pulls.extend([pull['number'] for pull in res])

            if len(pulls) < 25:
                break

        return pulls

    async def find_pull_request(self,
                                commit=None,
                                branch=None,
                                state='open',
                                token=None):
        query = '%srepo:%s+type:pr%s' % (
            (('%s+' % commit) if commit else ''), url_escape(self.slug),
            (('+state:%s' % state) if state else ''))

        # https://developer.github.com/v3/search/#search-issues
        res = await self.api('get', '/search/issues?q=%s' % query, token=token)
        if res['items']:
            return res['items'][0]['number']

    async def list_top_level_files(self, ref, token=None):
        # https://developer.github.com/v3/repos/contents/#get-contents
        content = await self.api(
            'get',
            f'/repos/{self.slug}/contents',
            ref=ref,
            token=token)
        return [
            {
                'name': f['name'],
                'path': f['path'],
                'type': self._github_type_to_torngit_type(f['type'])
            } for f in content
        ]

    def _github_type_to_torngit_type(self, val):
        if val == 'file':
            return 'file'
        elif val == 'dir':
            return 'folder'
        return 'other'

    async def get_ancestors_tree(self, commitid, token=None):
        res = await self.api(
            'get', '/repos/%s/commits' % self.slug,
            token=token,
            sha=commitid
        )
        start = res[0]['sha']
        commit_mapping = {val['sha']: [k['sha'] for k in val['parents']] for val in res}
        return self.build_tree_from_commits(start, commit_mapping)