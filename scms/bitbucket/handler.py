import os
from tornado import gen
import urllib as urllib_parse
from tornado.web import HTTPError
from tornado.auth import OAuthMixin
from tornado.escape import json_decode

from bitbucket import Bitbucket


class BitbucketHandler(Bitbucket, OAuthMixin):
    @gen.coroutine
    def api(self, path, version="1", callback=None, method="GET", access_token=None, body=None, **args):
        url = 'https://bitbucket.org/api/%s.0/%s' % (str(version), (path[1:] if path[0] == '/' else path))

        if not access_token:
            if self.current_user.oauth_token:
                access_token = dict(key=self.current_user.oauth_token, secret=self.current_user.oauth_secret)
            else:
                token = os.getenv('BITBUCKET_ACCESS_TOKEN')
                if token:
                    token = token.split(':')
                    access_token = dict(key=token[0], secret=token[1])

        if access_token:
            all_args = {}
            all_args.update(args)
            all_args.update(body or {})
            oauth = self._oauth_request_parameters(url, access_token, all_args, method=method)
            args.update(oauth)

        if args:
            url += "?" + urllib_parse.urlencode(args)

        try:
            res = yield self.fetch(url, method=method, body=urllib_parse.urlencode(body) if body else None,
                                   connect_timeout=self.async_timeouts[0], request_timeout=self.async_timeouts[1])

        except:
            raise

        else:
            if res.code == 204:
                raise gen.Return(None)

            elif 'application/json' in res.headers.get('Content-Type'):
                raise gen.Return(json_decode(res.body))

            else:
                raise gen.Return(res.body)

    @gen.coroutine
    def refresh_repo(self):
        if self['repo_service_id'] is None:
            # https://confluence.atlassian.com/display/BITBUCKET/repository+Resource#repositoryResource-GETarepository
            res = yield self.api("/".join(("repositories", self['username'], self['repo'])), version="2")
        else:
            res = yield self.api("/repositories/%%7B%(owner_service_id)s%%7D/%%7B%(repo_service_id)s%%7D" % self.data, version="2")
        username, repo = tuple(res['full_name'].split('/', 1))
        raise gen.Return(dict(owner_service_id=res['owner']['uuid'][1:-1], repo_service_id=res['uuid'][1:-1],
                              private=res['is_private'], branch='master',
                              username=username, repo=repo))

    @gen.coroutine
    def get_authenticated(self):
        if self['private']:
            # https://confluence.atlassian.com/bitbucket/repository-resource-423626331.html#repositoryResource-GETarepository
            yield self.api('/'.join(('repositories', self['username'], self['repo'])), version='2')
            raise gen.Return((True, True))
        else:
            # https://confluence.atlassian.com/bitbucket/user-endpoint-296092264.html#userEndpoint-GETalistofuserprivileges
            groups = yield self.api('/user/privileges')
            raise gen.Return((True, self['username'] in groups['teams']))

    @gen.coroutine
    def get_source(self, path, ref):
        content = yield self.api("/".join(("repositories", self['username'], self['repo'], "raw", ref, path)))
        raise gen.Return(content)

    @gen.coroutine
    def get_commit(self, commit):
        # https://confluence.atlassian.com/display/BITBUCKET/diff+Resource
        diff = yield self.api("/".join(("repositories", self['username'], self['repo'], 'diff', commit)), version="2")
        raise gen.Return(diff)

    @gen.coroutine
    def get_compare(self, base, head):
        # https://confluence.atlassian.com/display/BITBUCKET/diff+Resource
        # WATING ON https://bitbucket.org/site/master/issues/4779/ability-to-diff-between-any-two-commits
        raise HTTPError(404, reason="Bitbucket does not support a compare api yet. Read more here https://bitbucket.org/site/master/issues/4779/ability-to-diff-between-any-two-commits.")
