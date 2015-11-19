import os
import oauth2 as oauth
from tornado import gen
from urlparse import parse_qsl
from tornado.web import HTTPError
from tornado.auth import OAuthMixin
from tornado.escape import json_decode
from tornado.httputil import url_concat

from sign import signature
from app.helpers import metric
from app.base import BaseHandler
from bitbucket_server import BitbucketServerBase


class BitbucketServerHandler(BaseHandler, BitbucketServerBase, OAuthMixin):
    @gen.coroutine
    def api(self, path=None, callback=None, method="GET", access_token=None, body=None, url=None, **args):
        """
        This is NOT async atm...
        """

        # process desired api path
        if not url:
            assert path
            url = os.getenv('BITBUCKET_SERVER_URL') + '/rest/api/1.0/%s' % (path[1:] if path[0] == '/' else path)

        # process inline arguments
        if args:
            url = url_concat(url, args)

        # get accessing token
        if access_token:
            token = oauth.Token(*access_token)
        elif not self.current_user.guest:
            token = oauth.Token(self.current_user.oauth_token, self.current_user.oauth_secret)
        else:
            token = None

        # create oauth consumer
        client = oauth.Client(oauth.Consumer(os.getenv('BITBUCKET_SERVER_CLIENT_ID'), ''), token, **self.verify_ssl)
        client.set_signature_method(signature)

        response, content = client.request(url, method, body or '')
        status = int(response['status'])

        if status == 200:
            if 'application/json' in response.get('content-type'):
                raise gen.Return(json_decode(content))
            else:
                try:
                    content = dict(parse_qsl(content)) or content
                except:
                    pass

                raise gen.Return(content)

        elif status > 599:
            metric("source=bitbucket_server count#async.timeout=1\n")
            raise HTTPError(400, reason="Request to Bitbucket Server timed out. Please try again.")

        else:
            self.log(url=url, status=404, body=content)
            try:
                reason = "Response from Bitbucket Server: " + json_decode(content)['errors'][0]['message']
            except:
                reason = None
            raise HTTPError(status, reason=reason)

    @gen.coroutine
    def get_authenticated(self):
        """
        if private then can tap
        if private then current user
        """
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp1889424
        if self['private']:
            yield self.api('/'.join(('projects', self.project.upper(), 'repos', self['repo'] or self['repo'])))
        raise gen.Return((True, True))

    @gen.coroutine
    def refresh_repo(self):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp1889424
        res = yield self.api('/'.join(('projects', self.project.upper(), 'repos', self['repo'] or self['repo'])))
        username = res['project']['key']
        owner_service_id = res['project']['id']
        if res['project']['type'] == 'PERSONAL':
            owner_service_id = 'U%d' % res['project']['owner']['id']

        raise gen.Return(dict(owner_service_id=owner_service_id, repo_service_id=res['id'],
                              private=(not res.get('public', res.get('origin', {}).get('public'))), branch='master',
                              username=username, repo=res['slug']))

    @gen.coroutine
    def get_source(self, path, ref):
        page = 0
        content = []
        url = "/".join(('projects', self.project, 'repos', self['repo'], 'browse', path))
        while True:
            page += 1
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2028128
            res = yield self.api(url, at=ref, page=page)
            content.extend(res['lines'])
            if res['isLastPage']:
                break
            del res

        raise gen.Return('\n'.join(map(lambda a: a.get('text', ''), content)))

    @gen.coroutine
    def get_commit(self, commit):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3120016
        diff = yield self.api('/'.join(('projects', self.project, 'repos', self['repo'], 'commits', commit, 'diff')))
        raise gen.Return(diff)

    @gen.coroutine
    def get_compare(self, base, head):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3370768
        diff = yield self.api('/'.join(('projects', self.project, 'repos', self['repo'], 'commits', head, 'diff')),
                              withComments=False, whitespace='ignore-all', contextLines=3, since=base)
        raise gen.Return(diff)
