import os
from time import time
from tornado import gen
from tornado.auth import OAuth2Mixin
from tornado.escape import json_decode
from tornado.escape import json_encode
from tornado.httputil import url_concat

from github import GithubBase
from app.helpers import metric
from app.base import BaseHandler


class GithubHandler(GithubBase, BaseHandler, OAuth2Mixin):
    @gen.coroutine
    def api(self, path, callback=None, access_token=None, method='GET', body=None, headers=None, **args):
        _headers = {"Accept": "application/json",
                    "User-Agent": "Codecov",
                    "Authorization": "token %s" % (access_token or self.current_user.oauth_token or os.getenv("%s_ACCESS_TOKEN" % self.service.upper()))}
        _headers.update(headers or {})

        on_behalf_of = 'user' if access_token or self.current_user.oauth_token else 'codecov'

        url = url_concat("/".join((self.api_url, (path[1:] if path[0] == '/' else path))), args).replace(' ', '%20')
        eta = time()
        try:
            res = yield self.fetch(url, method=method, body=json_encode(body) if body else None, headers=_headers,
                                   ca_certs=self.verify_ssl,
                                   connect_timeout=self.async_timeouts[0], request_timeout=self.async_timeouts[1])

        except:
            raise

        else:
            if res.code == 204:
                raise gen.Return(None)

            elif res.headers.get('Content-Type')[:16] == 'application/json':
                raise gen.Return(json_decode(res.body))

            else:
                raise gen.Return(res.body)

        finally:
            async = int((time() - eta) * 1000)
            self._log_data['async'] = self._log_data.get('async', 0) + async
            metric("source=%s measure#async.speed=%dms\n" % (self.service, async))
            try:
                # https://developer.github.com/v3/#rate-limiting
                remaining = int(res.headers.get("X-RateLimit-Remaining"))
                if self.current_user.gest:
                    metric("source=%s count#ratelimit.count=%d\n" % (self.service, remaining))
                self._log_data["ratelimit"] = "%(X-RateLimit-Remaining)s/%(X-RateLimit-Limit)s %(X-RateLimit-Reset)s" % res.headers
                self._log_data["obo"] = on_behalf_of
            except:
                pass

    @gen.coroutine
    def refresh_repo(self):
        if self['repo_service_id'] is None:
            # https://developer.github.com/v3/repos/#get
            res = yield self.api("/".join(("repos", self['username'], self['repo'])))
        else:
            res = yield self.api('repositories/' + str(self['repo_service_id']))
        username, repo = tuple(res['full_name'].split('/', 1))
        raise gen.Return(dict(owner_service_id=res['owner']['id'], repo_service_id=res['id'],
                              private=res['private'], branch=res['default_branch'] or 'master',
                              username=username, repo=repo))

    @gen.coroutine
    def get_authenticated(self):
        # https://developer.github.com/v3/repos/#get
        r = yield self.api("/".join(("repos", self['username'], self['repo'])))
        ok = r['permissions']['admin'] or r['permissions']['push']
        raise gen.Return((True, ok))

    @gen.coroutine
    def get_source(self, path, ref):
        # https://developer.github.com/v3/repos/contents/#get-contents
        content = yield self.api("/".join(("repos", self['username'], self['repo'], "contents", path)),
                                 ref=ref, headers={"Accept": "application/vnd.github.v3.raw"})
        raise gen.Return(content)

    @gen.coroutine
    def get_commit(self, commit):
        # https://developer.github.com/v3/repos/commits/#get-a-single-commit
        diff = yield self.api("/".join(("repos", self['username'], self['repo'], "commits", commit)),
                              headers={"Accept": "application/vnd.github.v3.diff"})
        raise gen.Return(diff)

    @gen.coroutine
    def get_compare(self, base, head):
        # https://developer.github.com/v3/repos/commits/#compare-two-commits
        diff = yield self.api("/".join(("repos", self['username'], self['repo'], "compare", base + "..." + head)),
                              headers={"Accept": "application/vnd.github.v3.diff"})
        raise gen.Return(diff)
