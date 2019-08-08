import os
import socket
from time import time
from sys import stdout
from base64 import b64decode
from json import loads, dumps

from tornado.httputil import urlencode
from tornado.httputil import url_concat
from tornado.httpclient import HTTPError as ClientError

from torngit.status import Status
from torngit.base import BaseHandler
from torngit.exceptions import ObjectNotFoundException


class Gitlab(BaseHandler):
    service = 'gitlab'
    service_url = 'https://gitlab.com'
    api_url = 'https://gitlab.com/api/v{}'
    urls = dict(
        owner='%(username)s',
        user='%(username)s',
        repo='%(username)s/%(name)s',
        issues='%(username)s/%(name)s/issues/%(issueid)s',
        commit='%(username)s/%(name)s/commit/%(commitid)s',
        commits='%(username)s/%(name)s/commits',
        compare='%(username)s/%(name)s/compare/%(base)s...%(head)s',
        create_file=
        '%(username)s/%(name)s/new/%(branch)s?file_name=%(path)s&content=%(content)s',
        src='%(username)s/%(name)s/blob/%(commitid)s/%(path)s',
        branch='%(username)s/%(name)s/tree/%(branch)s',
        pull='%(username)s/%(name)s/merge_requests/%(pullid)s',
        tree='%(username)s/%(name)s/tree/%(commitid)s')

    async def api(self, method, path, body=None, token=None, version=4,
                  **args):
        # http://doc.gitlab.com/ce/api
        if path[0] == '/':
            _log = dict(
                event='api',
                endpoint=path,
                method=method,
                bot=(token or self.token).get('username'))
        else:
            _log = {}

        path = (
            self.api_url.format(version) + path) if path[0] == '/' else path
        headers = {
            'Accept': 'application/json',
            'User-Agent': os.getenv('USER_AGENT', 'Default')
        }

        if type(body) is dict:
            headers['Content-Type'] = 'application/json'

        if token or self.token:
            headers['Authorization'] = 'Bearer %s' % (token
                                                      or self.token)['key']

        url = url_concat(path, args).replace(' ', '%20')
        kwargs = dict(
            method=method.upper(),
            body=dumps(body) if type(body) is dict else body,
            headers=headers,
            ca_certs=self.verify_ssl
            if type(self.verify_ssl) is not bool else None,
            validate_cert=self.verify_ssl
            if type(self.verify_ssl) is bool else None,
            connect_timeout=self._timeouts[0],
            request_timeout=self._timeouts[1])

        start = time()
        try:
            res = await self.fetch(url, **kwargs)
        except ClientError as e:
            if e.response is None:
                raise ClientError(
                    502,
                    'GitLab was not able to be reached. Response empty. Please try again.'
                )

            self.log(
                'error',
                'GitLab HTTP %s' % e.response.code,
                body=e.response.body,
                **_log)
            raise

        except socket.gaierror:
            raise ClientError(
                502,
                'GitLab was not able to be reached. Gateway 502. Please try again.'
            )

        else:
            self.log('info', 'GitLab HTTP %s' % res.code, **_log)
            return None if res.code == 204 else loads(res.body)

        finally:
            stdout.write("source=%s measure#service=%dms\n" %
                         (self.service, int((time() - start) * 1000)))

    async def get_authenticated_user(self, **kwargs):
        creds = self._oauth_consumer_token()
        creds = dict(client_id=creds['key'], client_secret=creds['secret'])
        kwargs.update(creds)

        # http://doc.gitlab.com/ce/api/oauth2.html
        res = await self.api(
            'post',
            self.service_url + '/oauth/token',
            body=urlencode(
                dict(
                    code=self.get_argument('code'),
                    grant_type='authorization_code',
                    redirect_uri=self.get_url('/login/' + self.service),
                    **creds)))

        self.set_token(dict(key=res['access_token']))
        user = await self.api('get', '/user')
        user.update(res)
        return user

    async def post_webhook(self, name, url, events, secret, token=None):
        # http://doc.gitlab.com/ce/api/projects.html#add-project-hook
        res = await self.api(
            'post',
            '/projects/%s/hooks' % self.data['repo']['service_id'],
            body=dict(
                url=url,
                enable_ssl_verification=self.verify_ssl if isinstance(self.verify_ssl, bool) else True,
                **events),
            token=token)
        return res

    async def edit_webhook(self, hookid, name, url, events, secret,
                           token=None):
        # http://doc.gitlab.com/ce/api/projects.html#edit-project-hook
        return await self.api(
            'put',
            '/projects/%s/hooks/%s' % (self.data['repo']['service_id'],
                                       hookid),
            body=dict(
                url=url,
                enable_ssl_verification=self.verify_ssl
                if type(self.verify_ssl) is bool else True,
                **events),
            token=token)

    async def delete_webhook(self, hookid, token=None):
        # http://docs.gitlab.com/ce/api/projects.html#delete-project-hook
        try:
            await self.api(
                'delete',
                '/projects/%s/hooks/%s' % (self.data['repo']['service_id'],
                                           hookid),
                token=token)
        except ClientError as ce:
            if ce.code == 404:
                raise ObjectNotFoundException(f"Webhook with id {hookid} does not exist")
            raise
        return True

    def diff_to_json(self, diff):
        if type(diff) is list:
            for d in diff:
                mode = ''
                if d['deleted_file']:
                    mode = 'deleted file mode\n'
                d['diff'] = ('diff --git a/%(old_path)s b/%(new_path)s\n' %
                             d) + mode + d['diff']
            return super().diff_to_json(
                '\n'.join(map(lambda a: a['diff'], diff)))
        else:
            return super().diff_to_json(self, diff)

    async def list_repos(self, username=None, token=None):
        """
        V4 will return ALL projects, so we need to loop groups first
        """
        user = await self.api('get', '/user', token=token)
        user['is_user'] = True
        if username:
            if username.lower() == user['username'].lower():
                # just me
                groups = [user]
            else:
                # a group
                groups = [(await self.api(
                    'get', '/groups/{}'.format(username), token=token))]
        else:
            # user and all groups
            groups = await self.api('get', '/groups?per_page=100', token=token)
            groups.append(user)

        data = []
        for group in groups:
            page = 0
            while True:
                page += 1
                # http://doc.gitlab.com/ce/api/projects.html#projects
                if group.get('is_user'):
                    repos = await self.api(
                        'get',
                        '/projects?owned=true&per_page=50&page={}'.format(
                            page),
                        token=token)
                else:
                    repos = await self.api(
                        'get',
                        '/groups/{}/projects?per_page=50&page={}'.format(
                            group['id'], page),
                        token=token)
                for repo in repos:
                    data.append(
                        dict(
                            owner=dict(
                                service_id=repo['namespace']['id'],
                                username=repo['namespace']['path']),
                            repo=dict(
                                service_id=repo['id'],
                                name=repo['path'],
                                fork=None,
                                private=(repo['visibility'] != 'public'),
                                language=None,
                                branch=(repo['default_branch']
                                        or 'master'))))
                if len(repos) < 50:
                    break

        return data

    async def list_teams(self, token=None):
        # https://docs.gitlab.com/ce/api/groups.html#list-groups
        groups = await self.api('get', '/groups?per_page=100', token=token)
        return [
            dict(name=g['name'], id=g['id'], username=g['path'])
            for g in groups
        ]

    async def get_pull_request(self, pullid, token=None):
        # https://docs.gitlab.com/ce/api/merge_requests.html#get-single-mr
        try:
            pull = await self.api(
                'get',
                '/projects/{}/merge_requests/{}'.format(
                    self.data['repo']['service_id'], pullid),
                token=token)
        except ClientError as ce:
            if ce.code == 404:
                raise ObjectNotFoundException(f"PR with id {pullid} does not exist")
            raise

        if pull:
            # get first commit on pull
            parent = None
            try:
                # get list of commits and first one out
                first_commit = (await self.api(
                    'get',
                    '/projects/{}/merge_requests/{}/commits'.format(
                        self.data['repo']['service_id'], pullid),
                    token=token))[-1]
                if len(first_commit['parent_ids']) > 0:
                    parent = first_commit['parent_ids'][0]
                else:
                    # try querying the parent commit for this parent
                    parent = (await self.api(
                        'get',
                        '/projects/{}/repository/commits/{}'.format(
                            self.data['repo']['service_id'],
                            first_commit['id']),
                        token=token))['parent_ids'][0]
            except Exception:
                pass

            if pull['state'] == 'locked':
                pull['state'] = 'closed'

            return dict(
                base=dict(
                    branch=pull['target_branch'] or ''
                ),
                head=dict(
                    branch=pull['source_branch'] or '',
                    commitid=pull['sha']
                ),
                state='open' if pull['state'] in ('opened', 'reopened') else pull['state'],
                title=pull['title'],
                id=str(pull['iid']),
                number=str(pull['iid'])
            )

    async def set_commit_status(self,
                                commit,
                                status,
                                context,
                                description,
                                url,
                                coverage=None,
                                merge_commit=None,
                                token=None):
        # https://docs.gitlab.com/ce/api/commits.html#post-the-build-status-to-a-commit
        status = dict(error='failed', failure='failed').get(status, status)
        try:
            res = await self.api(
                'post',
                '/projects/%s/statuses/%s' % (self.data['repo']['service_id'],
                                              commit),
                body=dict(
                    state=status,
                    target_url=url,
                    coverage=coverage,
                    name=context,
                    description=description),
                token=token)
        except ClientError as ce:
            raise

        if merge_commit:
            await self.api(
                'post',
                '/projects/%s/statuses/%s' % (self.data['repo']['service_id'],
                                              merge_commit[0]),
                body=dict(
                    state=status,
                    target_url=url,
                    coverage=coverage,
                    name=merge_commit[1],
                    description=description),
                token=token)
        return res

    async def get_commit_statuses(self, commit, _merge=None, token=None):
        # http://doc.gitlab.com/ce/api/commits.html#get-the-status-of-a-commit
        statuses = await self.api(
            'get',
            '/projects/%s/repository/commits/%s/statuses' %
            (self.data['repo']['service_id'], commit),
            token=token)
        _states = dict(
            pending='pending',
            success='success',
            error='failure',
            failure='failure',
            cancelled='failure')
        statuses = [{
            'time': s.get('finished_at', s.get('created_at')),
            'state': _states.get(s['status']),
            'description': s['description'],
            'url': s.get('target_url'),
            'context': s['name']
        } for s in statuses]

        return Status(statuses)

    async def post_comment(self, pullid, body, token=None):
        # http://doc.gitlab.com/ce/api/notes.html#create-new-merge-request-note
        return await self.api(
            'post',
            '/projects/%s/merge_requests/%s/notes' %
            (self.data['repo']['service_id'], pullid),
            body=dict(body=body),
            token=token)

    async def edit_comment(self, pullid, commentid, body, token=None):
        # http://doc.gitlab.com/ce/api/notes.html#modify-existing-merge-request-note
        try:
            return await self.api(
                'put',
                '/projects/%s/merge_requests/%s/notes/%s' %
                (self.data['repo']['service_id'], pullid, commentid),
                body=dict(body=body),
                token=token)
        except ClientError as ce:
            if ce.code == 404:
                raise ObjectNotFoundException(f"Comment {commentid} in PR {pullid} does not exist")
            raise

    async def delete_comment(self, pullid, commentid, token=None):
        # https://docs.gitlab.com/ce/api/notes.html#delete-a-merge-request-note
        try:
            await self.api(
                'delete',
                '/projects/%s/merge_requests/%s/notes/%s' %
                (self.data['repo']['service_id'], pullid, commentid),
                token=token)
        except ClientError as ce:
            if ce.code == 404:
                raise ObjectNotFoundException(f"Comment {commentid} in PR {pullid} does not exist")
            raise
        return True

    async def get_commit(self, commit, token=None):
        # http://doc.gitlab.com/ce/api/commits.html#get-a-single-commit
        try:
            res = await self.api(
                'get',
                '/projects/%s/repository/commits/%s' %
                (self.data['repo']['service_id'], commit),
                token=token)
        except ClientError as ce:
            if ce.code == 404:
                raise ObjectNotFoundException
            raise
        # http://doc.gitlab.com/ce/api/users.html
        email = res['author_email']
        name = res['author_name']
        _id = None
        username = None
        authors = await self.api(
            'get', '/users', search=email or name, token=token)
        if authors:
            for author in authors:
                if author['name'] == name or author.get('email') == email:
                    _id = authors[0]['id']
                    username = authors[0]['username']
                    name = authors[0]['name']
                    break

        return dict(
            author=dict(id=_id, username=username, email=email, name=name),
            message=res['message'],
            parents=res['parent_ids'],
            commitid=commit,
            timestamp=res['committed_date']
        )

    async def get_pull_request_commits(self, pullid, token=None):
        # http://doc.gitlab.com/ce/api/merge_requests.html#get-single-mr-commits
        commits = await self.api(
            'get',
            '/projects/{}/merge_requests/{}/commits'.format(
                self.data['repo']['service_id'], pullid),
            token=token)
        return [c['id'] for c in commits]

    async def get_branches(self, token=None):
        # http://doc.gitlab.com/ce/api/projects.html#list-branches
        res = await self.api(
            'get',
            '/projects/%s/repository/branches' %
            self.data['repo']['service_id'],
            token=token)
        return [(b['name'], b['commit']['id']) for b in res]

    async def get_pull_requests(self, state='open', token=None):
        # ONLY searchable by branch.
        state = {
            'merged': 'merged',
            'open': 'opened',
            'close': 'closed'
        }.get(state, 'all')
        # [TODO] pagination coming soon
        # http://doc.gitlab.com/ce/api/merge_requests.html#list-merge-requests
        res = await self.api(
            'get',
            '/projects/%s/merge_requests?state=%s' %
            (self.data['repo']['service_id'], state),
            token=token)
        # first check if the sha matches
        return [pull['iid'] for pull in res]

    async def find_pull_request(self,
                                commit=None,
                                branch=None,
                                state='open',
                                token=None):
        # ONLY searchable by branch.
        state = {
            'merged': 'merged',
            'open': 'opened',
            'close': 'closed'
        }.get(state, 'all')

        # [TODO] pagination coming soon
        # http://doc.gitlab.com/ce/api/merge_requests.html#list-merge-requests
        try:
            res = await self.api(
                'get',
                '/projects/%s/merge_requests?state=%s' %
                (self.data['repo']['service_id'], state),
                token=token)
        except ClientError as e:
            if e.code == 403:
                # will get 403 if merge requests are disabled on gitlab
                return None
            raise

        # first check if the sha matches
        if commit:
            for pull in res:
                if pull['sha'] == commit:
                    return pull['iid']

        elif branch:
            for pull in res:
                if (pull['source_branch'] and pull['source_branch'] == branch):
                    return pull['iid']

        else:
            return res[0]['iid']

    async def get_authenticated(self, token=None):
        # http://doc.gitlab.com/ce/api/projects.html#get-single-project
        # http://doc.gitlab.com/ce/permissions/permissions.html
        can_edit = False
        try:
            res = await self.api(
                'get',
                '/projects/%s' % self.data['repo']['service_id'],
                token=token)
            permission = max(
                [
                    (res['permissions']['group_access'] or {}).get('access_level') or 0,
                    (res['permissions']['project_access'] or {}).get('access_level') or 0
                ])
            can_edit = permission > 20
        except ClientError:
            if self.data['repo']['private']:
                raise

        return (True, can_edit)

    async def get_is_admin(self, user, token=None):
        # https://docs.gitlab.com/ce/api/members.html#get-a-member-of-a-group-or-project
        user_id = int(user['service_id'])
        res = await self.api(
            'get',
            '/groups/{}/members/{}'.format(self.data['owner']['service_id'],
                                           user_id),
            token=token)
        return bool(res['state'] == 'active' and res['access_level'] > 39)

    async def get_commit_diff(self, commit, context=None, token=None):
        # http://doc.gitlab.com/ce/api/commits.html#get-the-diff-of-a-commit
        res = await self.api(
            'get',
            '/projects/%s/repository/commits/%s/diff' %
            (self.data['repo']['service_id'], commit),
            token=token)
        return self.diff_to_json(res)

    async def get_repository(self, token=None):
        # https://docs.gitlab.com/ce/api/projects.html#get-single-project
        if self.data['repo'].get('service_id') is None:
            res = await self.api(
                'get',
                '/projects/' + self.slug.replace('/', '%2F'),
                token=token)
        else:
            res = await self.api(
                'get',
                '/projects/' + self.data['repo']['service_id'],
                token=token)
        owner = res['namespace']
        username, repo = tuple(res['path_with_namespace'].split('/', 1))
        return (dict(
            owner=dict(service_id=owner['id'], username=username),
            repo=dict(
                service_id=res['id'],
                private=res['visibility'] != 'public',
                language=None,
                branch=(res['default_branch'] or 'master'),
                name=repo)))

    async def get_source(self, path, ref, token=None):
        # https://docs.gitlab.com/ce/api/repository_files.html#get-file-from-repository
        try:
            res = await self.api(
                'get',
                '/projects/{}/repository/files/{}'.format(
                    self.data['repo']['service_id'],
                    urlencode(dict(a=path))[2:]),
                ref=ref,
                token=token)
        except ClientError as ce:
            if ce.code == 404:
                raise ObjectNotFoundException(f"Path {path} not found at {ref}")
            raise

        return (dict(commitid=None, content=b64decode(res['content'])))

    async def get_compare(self,
                          base,
                          head,
                          context=None,
                          with_commits=True,
                          token=None):
        # https://docs.gitlab.com/ee/api/repositories.html#compare-branches-tags-or-commits
        compare = await self.api(
            'get',
            '/projects/{}/repository/compare/?from={}&to={}'.format(
                self.data['repo']['service_id'], base, head),
            token=token)

        return dict(
            diff=self.diff_to_json(compare['diffs']),
            commits=[
                dict(
                    commitid=c['id'],
                    message=c['title'],
                    timestamp=c['created_at'],
                    author=dict(
                        email=c['author_email'], name=c['author_name']))
                for c in compare['commits']
            ][::-1])
