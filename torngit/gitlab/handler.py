import os
from time import time
from tornado import gen
from base64 import b64decode
from tornado.auth import OAuth2Mixin
from tornado.escape import json_decode
from tornado.escape import json_encode
from tornado.httputil import url_concat

from gitlab import GitlabBase
from app.helpers import metric
from app.handlers.base import BaseHandler


class GitlabHandler(GitlabBase, BaseHandler, OAuth2Mixin):
    @gen.coroutine
    def api(self, path, callback=None, access_token=None, method='GET', body=None, headers=None, **args):
        _headers = {"Accept": "application/json", "User-Agent": "Codecov",
                    "Authorization": "Bearer %s" % (access_token or self.current_user.oauth_token or os.getenv("%s_ACCESS_TOKEN" % self.service.upper()))}

        _headers.update(headers or {})

        # http://doc.gitlab.com/ce/api
        eta = time()
        url = url_concat("/".join((self.service_url, "api/v3", (path[1:] if path[0] == '/' else path))), args).replace(' ', '%20')
        try:
            res = yield self.fetch(url, method=method, body=json_encode(body) if body else None, headers=_headers,
                                   ca_certs=self.verify_ssl,
                                   connect_timeout=self.async_timeouts[0], request_timeout=self.async_timeouts[1])

        except:
            raise

        else:
            if res.code == 204:
                raise gen.Return(None)

            raise gen.Return(json_decode(res.body))

        finally:
            async = int((time() - eta) * 1000)
            self._log_data['async'] = self._log_data.get('async', 0) + async
            metric("source=%s measure#async.speed=%dms\n" % (self.service, async))

    @gen.coroutine
    def get_authenticated(self):
        # http://doc.gitlab.com/ce/api/projects.html#get-single-project
        # http://doc.gitlab.com/ce/permissions/permissions.html
        # http://doc.gitlab.com/ce/api/groups.html#group-members
        can_edit = False
        try:
            res = yield self.api("/".join(("projects", str(self['repo_service_id']))))
            permission = max([(res['permissions']['group_access'] or {}).get('access_level', 0),
                              (res['permissions']['project_access'] or {}).get('access_level', 0)])
            can_edit = permission > 20
        except:
            if self['private']:
                raise

        raise gen.Return((True, can_edit))

    @gen.coroutine
    def refresh_repo(self):
        if self['repo_service_id'] is None:
            # http://doc.gitlab.com/ce/api/projects.html#get-single-project
            res = yield self.api("/".join(("projects", self['username']+"%2F"+self['repo'])))
        else:
            res = yield self.api("/".join(("projects", str(self['repo_service_id']))))
        owner = res['namespace']
        username, repo = tuple(res['path_with_namespace'].split('/', 1))
        raise gen.Return(dict(owner_service_id=owner['owner_id'] or owner['id'], repo_service_id=res['id'],
                              private=not res['public'], branch=res['default_branch'] or 'master',
                              username=username, repo=repo))

    @gen.coroutine
    def get_source(self, path, ref):
        # http://doc.gitlab.com/ce/api/repository_files.html
        content = yield self.api("/".join(("projects", self['repo_service_id'], "repository", "files")),
                                 ref=ref, file_path=path)
        raise gen.Return(b64decode(content['content']))

    @gen.coroutine
    def get_commit(self, commit):
        # http://doc.gitlab.com/ce/api/commits.html#get-the-diff-of-a-commit
        diff = yield self.api("/".join(("projects", self['repo_service_id'], "repository", "commits", commit, 'diff')))
        raise gen.Return(diff)

    @gen.coroutine
    def get_compare(self, base, head):
        # http://doc.gitlab.com/ce/api/repositories.html#compare-branches-tags-or-commits
        diff = yield self.api(self.service, "/".join(("projects", self['repo_service_id'], "compare")),
                              **{"from": base, "to": head})
        raise gen.Return(diff)
