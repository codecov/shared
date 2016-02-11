import os
from tornado import gen
from base64 import b64decode
from json import loads, dumps
from tornado.httputil import urlencode
from tornado.httputil import url_concat

from torngit.status import Status
from torngit.base import BaseHandler


class Gitlab(BaseHandler):
    service = 'gitlab'
    service_url = 'https://gitlab.com'
    api_url = 'https://gitlab.com/api/v3'
    icon = 'fa-git'
    verify_ssl = None
    urls = dict(owner='%(username)s',
                repo='%(username)s/%(name)s',
                commit='%(username)s/%(name)s/commit/%(commitid)s',
                commits='%(username)s/%(name)s/commits',
                compare='%(username)s/%(name)s/compare/%(base)s...%(head)s',
                blob='%(username)s/%(name)s/blob/%(commitid)s/%(path)s',
                branch='%(username)s/%(name)s/tree/%(branch)s',
                pr='%(username)s/%(name)s/merge_requests/%(pr)s',
                tree='%(username)s/%(name)s/tree/%(commitid)s')

    @gen.coroutine
    def api(self, method, path, body=None, **args):
        # http://doc.gitlab.com/ce/api
        path = (self.api_url + path) if path[0] == '/' else path
        res = yield self.fetch(url_concat(path, args).replace(' ', '%20'),
                               method=method.upper(),
                               body=dumps(body) if type(body) is dict else body,
                               headers={'Accept': 'application/json',
                                        'User-Agent': os.getenv('USER_AGENT', 'Default'),
                                        'Authorization': 'Bearer '+self.token['key']},
                               ca_certs=self.verify_ssl if type(self.verify_ssl) is not bool else None,
                               validate_cert=self.verify_ssl if type(self.verify_ssl) is bool else None,
                               connect_timeout=self.timeouts[0],
                               request_timeout=self.timeouts[1])

        if res.code == 204:
            raise gen.Return(None)
        else:
            raise gen.Return(loads(res.body))

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
    def post_webhook(self, name, url, events, secret):
        # http://doc.gitlab.com/ce/api/projects.html#add-project-hook
        res = yield self.api('post', '/projects/%s/hooks' % self['repo']['service_id'],
                             body=dict(url=url,
                                       enable_ssl_verification=True,
                                       **events))
        raise gen.Return(res['id'])

    @gen.coroutine
    def edit_webhook(self, hookid, name, url, events, secret):
        # http://doc.gitlab.com/ce/api/projects.html#edit-project-hook
        yield self.api('put', '/projects/%s/hooks/%s' % (self['repo']['service_id'], hookid),
                       body=dict(url=url,
                                 enable_ssl_verification=True,
                                 **events))
        raise gen.Return(True)

    def diff_to_json(self, diff, report, context=True):
        for d in diff:
            mode = ''
            if d['deleted_file']:
                mode = 'deleted file mode\n'
            d['diff'] = ('diff --git a/%(old_path)s b/%(new_path)s\n' % d) + mode + d['diff']
        return super(Gitlab, self).diff_to_json('\n'.join(map(lambda a: a['diff'], diff)), report, context)

    @gen.coroutine
    def list_repos(self, username, ownerid):
        data, page = [], 0
        while True:
            page += 1
            # http://doc.gitlab.com/ce/api/projects.html#projects
            repos = yield self.api('get', '/projects?per_page=100&page=%d' % page)
            for repo in repos:
                owner = repo['namespace']
                data.append(dict(owner=dict(service_id=owner['owner_id'] or owner['id'],
                                            username=owner['path']),
                                 repo=dict(service_id=repo['id'],
                                           name=repo['path'],
                                           fork=None,
                                           private=not repo['public'],
                                           language=None,
                                           branch=repo['default_branch'] or 'master')))

            if len(repos) < 100:
                break

        raise gen.Return(data)

    @gen.coroutine
    def list_teams(self):
        # http://doc.gitlab.com/ce/api/groups.html#list-project-groups
        groups = yield self.api('get', '/groups')
        raise gen.Return([g['path'] for g in groups])

    @gen.coroutine
    def get_pull_request(self, pr):
        # http://doc.gitlab.com/ce/api/merge_requests.html
        res = yield self.api('get', '/projects/%s/merge_requests?iid=%s' % (self['repo']['service_id'], pr))
        for _pr in res:
            if str(_pr['iid']) == pr:
                head = yield self._get_head_of(_pr['target_branch'])
                base = yield self._get_head_of(_pr['source_branch'])
                raise gen.Return(dict(base=dict(branch=_pr['target_branch'],
                                                commitid=base),
                                      head=dict(branch=_pr['source_branch'],
                                                commitid=head),
                                      open=_pr['state'] == 'opened',
                                      merged=_pr['state'] == 'merged',
                                      title=_pr['title'],
                                      id=_pr['id'], number=pr))

    @gen.coroutine
    def _get_head_of(self, branch):
        # http://doc.gitlab.com/ce/api/branches.html#get-single-repository-branch
        res = yield self.api('get', '/projects/%s/repository/branches/%s' % (self['repo']['service_id'], branch))
        raise gen.Return(res['commit']['id'])

    @gen.coroutine
    def set_commit_status(self, commit, status, context, description, url, _merge=None):
        # http://doc.gitlab.com/ce/api/commits.html#post-the-status-to-commit
        status = dict(error='canceled', failure='failed').get(status, status)
        res = yield self.api('post', '/projects/%s/statuses/%s' % (self['repo']['service_id'], commit),
                             data=dict(state=status,
                                       target_url=url,
                                       name=context,
                                       description=description))
        raise gen.Return(res)

    @gen.coroutine
    def get_commit_statuses(self, commit, _merge=None):
        # http://doc.gitlab.com/ce/api/commits.html#get-the-status-of-a-commit
        statuses = yield self.api('get', '/projects/%s/repository/commits/%s/statuses' % (self['repo']['service_id'], commit))
        _states = dict(pending='pending', success='success', error='failure', failure='failure')
        statuses = [{'time': s.get('finished_at', s.get('created_at')),
                     'state': _states.get(s['state']),
                     'url': s.get('target_url'),
                     'context': s['name']} for s in statuses]

        raise gen.Return(Status(statuses))

    @gen.coroutine
    def post_comment(self, issueid, body):
        # http://doc.gitlab.com/ce/api/notes.html#create-new-merge-request-note
        res = yield self.api('post', '/projects/%s/merge_requests/%s/notes' % (self['repo']['service_id'], issueid),
                             data=dict(body=body))
        raise gen.Return(res['id'])

    @gen.coroutine
    def edit_comment(self, issueid, commentid, body):
        # http://doc.gitlab.com/ce/api/notes.html#modify-existing-merge-request-note
        yield self.api('put', '/projects/%s/merge_requests/%s/notes/%s' % (self['repo']['service_id'], issueid, commentid),
                       data=dict(body=body))
        raise gen.Return(True)

    def delete_comment(self, issueid, commentid):
        # not implemented by gitlab yet
        # $('.note').each(function(){ console.log($(this).attr('id').substr(5));
        #     $.ajax({'method': 'delete', 'url': 'https://gitlab.com/codecov/ci-repo/notes/'+$(this).attr('id').substr(5)});
        # });
        return False

    @gen.coroutine
    def get_commit(self, commitid):
        # http://doc.gitlab.com/ce/api/commits.html#get-a-single-commit
        res = yield self.api('get', '/projects/%s/repository/commits/%s' % (self['repo']['service_id'], commitid))

        # http://doc.gitlab.com/ce/api/users.html
        authors = yield self.api('get', '/users?search='+res['author_name'])
        author_id = (filter(lambda a: a['username'] == res['author_name'], authors) or [dict(id=None)])[0]['id']

        raise gen.Return(dict(author=dict(id=author_id,
                                          username=res['author_name'],
                                          email=res['author_email'],
                                          name=res['author_name']),
                              message=res['message'],
                              commitid=commitid,
                              date=res['committed_date']))

    @gen.coroutine
    def get_pull_request_commits(self, pullid):
        data, page = [], 0
        while True:
            page += 1
            # http://doc.gitlab.com/ce/api/merge_requests.html#get-single-mr-commits
            commits = yield self.api('get', '/projects/%s/merge_requests/%s/commits?per_page=100&page=%d' % (self['repo']['service_id'], pullid, page))
            data.extend([c['id'] for c in commits])
            if len(commits) < 100:
                break

        raise gen.Return(data)

    @gen.coroutine
    def get_branches(self):
        # http://doc.gitlab.com/ce/api/projects.html#list-branches
        res = yield self.api('get', '/projects/%s/repository/branches' % self['repo']['service_id'])
        raise gen.Return([(b['name'], b['commit']['id']) for b in res])

    @gen.coroutine
    def get_pull_requests(self, commitid=None, branch=None, state='open'):
        if commitid:
            raise NotImplemented('dont know how to search by commitid yet')

        # http://doc.gitlab.com/ce/api/merge_requests.html#list-merge-requests
        state = {'merged': 'merged', 'open': 'opened', 'close': 'closed'}.get(state, 'all')
        res = yield self.api('get', '/projects/%s/merge_requests?state=%s' % (self['repo']['service_id'], state))
        pulls = [b['iid']
                 for b in res
                 if branch is None or b['source_branch'] == branch]
        raise gen.Return(pulls)

        # [TODO] filter out based on commit exists in branh

    @gen.coroutine
    def get_authenticated(self):
        # http://doc.gitlab.com/ce/api/projects.html#get-single-project
        # http://doc.gitlab.com/ce/permissions/permissions.html
        # http://doc.gitlab.com/ce/api/groups.html#group-members
        can_edit = False
        try:
            res = yield self.api('get', '/projects/'+str(self['repo']['service_id']))
            permission = max([(res['permissions']['group_access'] or {}).get('access_level', 0),
                              (res['permissions']['project_access'] or {}).get('access_level', 0)])
            can_edit = permission > 20
        except:
            if self['private']:
                raise

        raise gen.Return((True, can_edit))

    @gen.coroutine
    def get_is_admin(self):
        pass

    @gen.coroutine
    def get_commit_diff(self, commitid, context=None):
        # http://doc.gitlab.com/ce/api/commits.html#get-the-diff-of-a-commit
        res = yield self.api('get', '/projects/%s/repository/commits%s/diff' % (self['repo']['service_id'], commitid))
        raise gen.Return(self.diff_to_json(res))

    @gen.coroutine
    def get_repository(self):
        # http://doc.gitlab.com/ce/api/projects.html#get-single-project
        if self['repo']['service_id'] is None:
            res = yield self.api('get', '/projects/'+self.slug.replace('/', '%2F'))
        else:
            res = yield self.api('get', '/projects/'+self['repo']['service_id'])
        owner = res['namespace']
        username, repo = tuple(res['path_with_namespace'].split('/', 1))
        raise gen.Return(dict(owner=dict(service_id=owner['owner_id'] or owner['id'],
                                         username=username),
                              repo=dict(service_id=res['id'],
                                        private=not res['public'],
                                        language=None,
                                        branch=res['default_branch'] or 'master',
                                        name=repo)))

    @gen.coroutine
    def get_source(self, path, ref):
        # http://doc.gitlab.com/ce/api/repository_files.html
        res = yield self.api('get', '/projects/%s/repository/files' % self['repo']['service_id'],
                             ref=ref, file_path=path)
        raise gen.Return(dict(commitid=res['commit_id'],
                              content=b64decode(res['content'])))

    @gen.coroutine
    def get_compare(self, base, head, context=None, with_commits=True):
        # http://doc.gitlab.com/ce/api/repositories.html#compare-branches-tags-or-commits
        compare = yield self.api('get', '/projects/%s/repository/compare/?from=%s&to=%s' % (self['repo']['service_id'], base, head))
        raise gen.Return(dict(diff=self.diff_to_json(compare['diffs']),
                              commits=[dict(commitid=c['id'],
                                            message=c['title'],
                                            date=c['created_at'],
                                            author=c['author_email']) for c in compare['commits']]))
