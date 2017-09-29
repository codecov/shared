import os
import socket
from time import time
from sys import stdout
from tornado import gen
from base64 import b64decode
from json import loads, dumps
from tornado.httputil import urlencode
from tornado.httputil import url_concat
from tornado.httpclient import HTTPError as ClientError

from torngit.status import Status
from torngit.base import BaseHandler


class Gitlab(BaseHandler):
    service = 'gitlab'
    service_url = 'https://gitlab.com'
    api_url = 'https://gitlab.com/api/v3'
    urls = dict(owner='%(username)s',
                user='%(username)s',
                repo='%(username)s/%(name)s',
                issues='%(username)s/%(name)s/issues/%(issueid)s',
                commit='%(username)s/%(name)s/commit/%(commitid)s',
                commits='%(username)s/%(name)s/commits',
                compare='%(username)s/%(name)s/compare/%(base)s...%(head)s',
                create_file='%(username)s/%(name)s/new/%(branch)s?file_name=%(path)s&content=%(content)s',
                src='%(username)s/%(name)s/blob/%(commitid)s/%(path)s',
                branch='%(username)s/%(name)s/tree/%(branch)s',
                pull='%(username)s/%(name)s/merge_requests/%(pullid)s',
                tree='%(username)s/%(name)s/tree/%(commitid)s')

    @gen.coroutine
    def api(self, method, path, body=None, token=None, **args):
        # http://doc.gitlab.com/ce/api
        if path[0] == '/':
            _log = dict(event='api',
                        endpoint=path,
                        method=method,
                        bot=(token or self.token).get('username'))
        else:
            _log = {}

        path = (self.api_url + path) if path[0] == '/' else path
        headers = {
            'Accept': 'application/json',
            'User-Agent': os.getenv('USER_AGENT', 'Default')
        }

        if type(body) is dict:
            headers['Content-Type'] = 'application/json'

        if token or self.token:
            headers['Authorization'] = 'Bearer %s' % (token or self.token)['key']

        url = url_concat(path, args).replace(' ', '%20')
        kwargs = dict(method=method.upper(),
                      body=dumps(body) if type(body) is dict else body,
                      headers=headers,
                      ca_certs=self.verify_ssl if type(self.verify_ssl) is not bool else None,
                      validate_cert=self.verify_ssl if type(self.verify_ssl) is bool else None,
                      connect_timeout=self._timeouts[0],
                      request_timeout=self._timeouts[1])

        start = time()
        try:
            res = yield self.fetch(url, **kwargs)

        except ClientError as e:
            if e.response is None:
                raise ClientError(502, 'GitLab was not able to be reached. Response empty. Please try again.')

            self.log('error',
                     'GitLab HTTP %s' % e.response.code,
                     body=e.response.body,
                     **_log)

            raise

        except socket.gaierror:
            raise ClientError(502, 'GitLab was not able to be reached. Gateway 502. Please try again.')

        else:
            self.log('info',
                     'GitLab HTTP %s' % res.code,
                     **_log)
            raise gen.Return(None if res.code == 204 else loads(res.body))

        finally:
            stdout.write("source=%s measure#service=%dms\n" % (self.service, int((time() - start) * 1000)))

    @gen.coroutine
    def get_authenticated_user(self):
        kwargs = dict(code=self.get_argument("code"))
        creds = self._oauth_consumer_token()
        creds = dict(client_id=creds['key'], client_secret=creds['secret'])
        kwargs.update(creds)

        # http://doc.gitlab.com/ce/api/oauth2.html
        res = yield self.api('post', self.service_url+'/oauth/token',
                             body=urlencode(dict(code=self.get_argument('code'),
                                                 grant_type='authorization_code',
                                                 redirect_uri=self.get_url('/login/'+self.service),
                                                 **creds)))

        self.set_token(dict(key=res['access_token']))
        user = yield self.api('get', '/user')
        user.update(res)
        raise gen.Return(user)

    @gen.coroutine
    def post_webhook(self, name, url, events, secret, token=None):
        # http://doc.gitlab.com/ce/api/projects.html#add-project-hook
        res = yield self.api('post', '/projects/%s/hooks' % self.data['repo']['service_id'],
                             body=dict(url=url,
                                       enable_ssl_verification=self.verify_ssl if type(self.verify_ssl) is bool else True,
                                       **events), token=token)
        raise gen.Return(res['id'])

    @gen.coroutine
    def edit_webhook(self, hookid, name, url, events, secret, token=None):
        # http://doc.gitlab.com/ce/api/projects.html#edit-project-hook
        yield self.api('put', '/projects/%s/hooks/%s' % (self.data['repo']['service_id'], hookid),
                       body=dict(url=url,
                                 enable_ssl_verification=self.verify_ssl if type(self.verify_ssl) is bool else True,
                                 **events), token=token)
        raise gen.Return(True)

    @gen.coroutine
    def delete_webhook(self, hookid, token=None):
        # http://docs.gitlab.com/ce/api/projects.html#delete-project-hook
        yield self.api('delete', '/projects/%s/hooks/%s' % (self.data['repo']['service_id'], hookid), token=token)
        raise gen.Return(True)

    def diff_to_json(self, diff):
        if type(diff) is list:
            for d in diff:
                mode = ''
                if d['deleted_file']:
                    mode = 'deleted file mode\n'
                d['diff'] = ('diff --git a/%(old_path)s b/%(new_path)s\n' % d) + mode + d['diff']
            return BaseHandler.diff_to_json(self, '\n'.join(map(lambda a: a['diff'], diff)))
        else:
            return BaseHandler.diff_to_json(self, diff)

    @gen.coroutine
    def list_repos(self, username=None, token=None):
        data, page = [], 0
        while True:
            page += 1
            # http://doc.gitlab.com/ce/api/projects.html#projects
            repos = yield self.api('get', '/projects?per_page=100&page=%d' % page, token=token)
            for repo in repos:
                owner = repo.get('owner', repo['namespace'])
                data.append(dict(owner=dict(service_id=owner['id'],
                                            username=owner.get('path', owner.get('username'))),
                                 repo=dict(service_id=repo['id'],
                                           name=repo.get('path', repo.get('name')),
                                           fork=None,
                                           private=not repo['public'],
                                           language=None,
                                           branch=(repo['default_branch'] or 'master').encode('utf-8', 'replace'))))

            if len(repos) < 100:
                break

        raise gen.Return(data)

    @gen.coroutine
    def list_teams(self, token=None):
        # https://docs.gitlab.com/ce/api/groups.html#list-groups
        groups = yield self.api('get', '/groups')
        raise gen.Return([dict(name=g['name'], id=g['id'], username=g['path']) for g in groups])

    @gen.coroutine
    def get_pull_request(self, pullid, token=None):
        # https://docs.gitlab.com/ce/api/merge_requests.html#get-single-mr
        pull = yield self.api('get', '/projects/{}/merge_requests?iid={}'.format(
            self.data['repo']['service_id'], pullid
        ), token=token)
        if pull:
            pull = pull[0]
            # get first commit on pull
            first_commit = (yield self.api('get', '/projects/{}/merge_requests/{}/commits'.format(
                self.data['repo']['service_id'], pull['id']
            ), token=token))[-1]['id']
            # get commit parent
            try:
                parent = (yield self.api('get', '/projects/{}/repository/commits/{}'.format(
                    self.data['repo']['service_id'], first_commit
                ), token=token))['parent_ids'][-1]
            except:
                parent = None

            if pull['state'] == 'locked':
                pull['state'] = 'closed'

            raise gen.Return(dict(base=dict(branch=(pull['target_branch'] or '').encode('utf-8', 'replace'),
                                            commitid=parent),
                                  head=dict(branch=(pull['source_branch'] or '').encode('utf-8', 'replace'),
                                            commitid=pull['sha']),
                                  state='open' if pull['state'] in ('opened', 'reopened') else pull['state'],
                                  title=pull['title'],
                                  id=str(pull['id']),
                                  number=str(pullid)))

    @gen.coroutine
    def set_commit_status(self, commit, status, context, description, url, merge_commit=None, coverage=None, token=None):
        # https://docs.gitlab.com/ce/api/commits.html#post-the-build-status-to-a-commit
        status = dict(error='failed', failure='failed').get(status, status)
        res = yield self.api('post', '/projects/%s/statuses/%s' % (self.data['repo']['service_id'], commit),
                             body=dict(state=status,
                                       target_url=url,
                                       name=context,
                                       description=description), token=token)

        if merge_commit:
            yield self.api('post', '/projects/%s/statuses/%s' % (self.data['repo']['service_id'], merge_commit[0]),
                           body=dict(state=status,
                                     target_url=url,
                                     name=merge_commit[1],
                                     description=description), token=token)
        raise gen.Return(res)

    @gen.coroutine
    def get_commit_statuses(self, commit, _merge=None, token=None):
        # http://doc.gitlab.com/ce/api/commits.html#get-the-status-of-a-commit
        statuses = yield self.api('get', '/projects/%s/repository/commits/%s/statuses' % (self.data['repo']['service_id'], commit), token=token)
        _states = dict(pending='pending', success='success', error='failure', failure='failure')
        statuses = [{'time': s.get('finished_at', s.get('created_at')),
                     'state': _states.get(s['status']),
                     'url': s.get('target_url'),
                     'context': s['name']} for s in statuses]

        raise gen.Return(Status(statuses))

    @gen.coroutine
    def post_comment(self, issueid, body, token=None):
        # http://doc.gitlab.com/ce/api/notes.html#create-new-merge-request-note
        res = yield self.api('post', '/projects/%s/merge_requests/%s/notes' % (self.data['repo']['service_id'], issueid),
                             body=dict(body=body), token=token)
        raise gen.Return(res['id'])

    @gen.coroutine
    def edit_comment(self, issueid, commentid, body, token=None):
        # http://doc.gitlab.com/ce/api/notes.html#modify-existing-merge-request-note
        yield self.api('put', '/projects/%s/merge_requests/%s/notes/%s' % (self.data['repo']['service_id'], issueid, commentid),
                       body=dict(body=body), token=token)
        raise gen.Return(commentid)

    def delete_comment(self, issueid, commentid, token=None):
        # https://docs.gitlab.com/ce/api/notes.html#delete-a-merge-request-note
        yield self.api('delete', '/projects/%s/merge_requests/%s/notes/%s' % (self.data['repo']['service_id'], issueid, commentid),
                       token=token)
        raise gen.Return(True)

    @gen.coroutine
    def get_commit(self, commit, token=None):
        # http://doc.gitlab.com/ce/api/commits.html#get-a-single-commit
        res = yield self.api('get', '/projects/%s/repository/commits/%s' % (self.data['repo']['service_id'], commit), token=token)

        # http://doc.gitlab.com/ce/api/users.html
        email = res['author_email']
        name = res['author_name']
        _id = None
        username = None
        authors = yield self.api('get', '/users', search=email or name, token=token)
        if authors:
            for author in authors:
                if author['name'] == name or author.get('email') == email:
                    _id = authors[0]['id']
                    username = authors[0]['username']
                    name = authors[0]['name']
                    break

        raise gen.Return(dict(author=dict(id=_id,
                                          username=username,
                                          email=email,
                                          name=name),
                              message=res['message'],
                              parents=res['parent_ids'],
                              commitid=commit,
                              timestamp=res['committed_date']))

    @gen.coroutine
    def get_pull_request_commits(self, pullid, token=None):
        # http://doc.gitlab.com/ce/api/merge_requests.html#get-single-mr-commits
        commits = yield self.api('get', '/projects/{0}/merge_requests/{1}/commits'.format(
            self.data['repo']['service_id'], pullid
        ), token=token)
        raise gen.Return([c['id'] for c in commits])

    @gen.coroutine
    def get_branches(self, token=None):
        # http://doc.gitlab.com/ce/api/projects.html#list-branches
        res = yield self.api('get', '/projects/%s/repository/branches' % self.data['repo']['service_id'], token=token)
        raise gen.Return([(b['name'], b['commit']['id']) for b in res])

    @gen.coroutine
    def get_pull_requests(self, state='open', token=None):
        # ONLY searchable by branch.
        state = {'merged': 'merged', 'open': 'opened', 'close': 'closed'}.get(state, 'all')
        merge_request_url = '/projects/%s/merge_requests/{0}/commits' % self.data['repo']['service_id']
        # [TODO] pagination coming soon
        # http://doc.gitlab.com/ce/api/merge_requests.html#list-merge-requests
        res = yield self.api('get', '/projects/%s/merge_requests?state=%s' % (self.data['repo']['service_id'], state),
                             token=token)
        # first check if the sha matches
        raise gen.Return([pull['iid'] for pull in res])

    @gen.coroutine
    def find_pull_request(self, commit=None, branch=None, state='open', token=None):
        # ONLY searchable by branch.
        state = {'merged': 'merged', 'open': 'opened', 'close': 'closed'}.get(state, 'all')
        merge_request_url = '/projects/%s/merge_requests/{0}/commits' % self.data['repo']['service_id']

        # [TODO] pagination coming soon
        # http://doc.gitlab.com/ce/api/merge_requests.html#list-merge-requests
        res = yield self.api('get', '/projects/%s/merge_requests?state=%s' % (self.data['repo']['service_id'], state),
                             token=token)
        # first check if the sha matches
        if commit:
            for pull in res:
                if pull['sha'] == commit:
                    raise gen.Return(pull['iid'])

        elif branch:
            branch = branch.encode('utf-8', 'replace') if branch else ''
            for pull in res:
                if (
                    pull['source_branch'] and
                    pull['source_branch'].encode('utf-8', 'replace') == branch
                ):
                    raise gen.Return(pull['iid'])

        else:
            raise gen.Return(res[0]['iid'])

    @gen.coroutine
    def get_authenticated(self, token=None):
        # http://doc.gitlab.com/ce/api/projects.html#get-single-project
        # http://doc.gitlab.com/ce/permissions/permissions.html
        can_edit = False
        try:
            res = yield self.api('get', '/projects/%s' % self.data['repo']['service_id'], token=token)
            permission = max([(res['permissions']['group_access'] or {}).get('access_level') or 0,
                              (res['permissions']['project_access'] or {}).get('access_level') or 0])
            can_edit = permission > 20
        except:
            if self.data['repo']['private']:
                raise

        raise gen.Return((True, can_edit))

    @gen.coroutine
    def get_is_admin(self, user, token=None):
        # http://doc.gitlab.com/ce/permissions/permissions.html#group
        user_id = int(user['service_id'])
        res = yield self.api('get', '/groups/%s/members' % self.data['owner']['service_id'], token=token)
        res = any(filter(lambda u: u and (u['id'] == user_id and u['access_level'] > 39), res))
        raise gen.Return(res)

    @gen.coroutine
    def get_commit_diff(self, commit, context=None, token=None):
        # http://doc.gitlab.com/ce/api/commits.html#get-the-diff-of-a-commit
        res = yield self.api('get', '/projects/%s/repository/commits/%s/diff' % (self.data['repo']['service_id'], commit), token=token)
        raise gen.Return(self.diff_to_json(res))

    @gen.coroutine
    def get_repository(self, token=None):
        # http://doc.gitlab.com/ce/api/projects.html#get-single-project
        if self.data['repo'].get('service_id') is None:
            res = yield self.api('get', '/projects/'+self.slug.replace('/', '%2F'), token=token)
        else:
            res = yield self.api('get', '/projects/'+self.data['repo']['service_id'], token=token)
        owner = res.get('owner', res['namespace'])
        username, repo = tuple(res['path_with_namespace'].split('/', 1))
        raise gen.Return(dict(owner=dict(service_id=owner['id'],
                                         username=username),
                              repo=dict(service_id=res['id'],
                                        private=not res['public'],
                                        language=None,
                                        branch=(res['default_branch'] or 'master').encode('utf-8', 'replace'),
                                        name=repo)))

    @gen.coroutine
    def get_source(self, path, ref, token=None):
        # http://doc.gitlab.com/ce/api/repository_files.html
        res = yield self.api('get', '/projects/%s/repository/files' % self.data['repo']['service_id'],
                             ref=ref,
                             file_path=path.replace(' ', '%20'),
                             token=token)

        raise gen.Return(dict(commitid=None,
                              content=b64decode(res['content'])))

    @gen.coroutine
    def get_compare(self, base, head, context=None, with_commits=True, token=None):
        # http://doc.gitlab.com/ce/api/repositories.html#compare-branches-tags-or-commits
        compare = yield self.api('get', '/projects/%s/repository/compare/?from=%s&to=%s' % (self.data['repo']['service_id'], base, head), token=token)
        raise gen.Return(dict(diff=self.diff_to_json(compare['diffs']),
                              commits=[dict(commitid=c['id'],
                                            message=c['title'],
                                            timestamp=c['created_at'],
                                            author=dict(email=c['author_email'],
                                                        name=c['author_name'])) for c in compare['commits']][::-1]))
