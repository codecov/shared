import os
import base64
import urllib
import oauth2 as oauth
from tornado import gen
from json import loads, dumps
from datetime import datetime
from urlparse import parse_qsl
from tornado.web import HTTPError
from tlslite.utils import keyfactory
from tornado.httputil import url_concat

from torngit.status import Status
from torngit.base import BaseHandler


PEM = """-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQC9d2iMTFiXglyvHmp5ExoNK2X8nxJ+1mlxgWOyTUpTrOKRiDUb
ZoZID3TP8CobQ5BsqDOSawHyi+Waf9Ca+iYoTu1fa8yZUreQXAdaK1u61Mn2XCkm
ITE/N5kvbYjDEWA1Dwb6CsvVkYZXo/Eq1X/3yrLXWKDNEnm0Cq48PFWqMQIDAQAB
AoGBAJ9wEqytuoeVDkXXhKXqayvV73cMrdXKvOTli24KGJgdjnQFeRtbxXhyeUxa
wDQ9QRYO3YdDQVpIW6kOEg+4nc4vEb4o2kiZTSq/OMkoO7NFM4AlsUbXB+lJ2Cgf
p0M4MjQVaMihvyXMw3qAFBNAAuwCYShau54rGTIbXJlODqN5AkEA4HPkM3JW8i11
xZLDYcwclYUhShx4WldNJkS0btoBwGrBt0NKiCR9dkZcZMLfFYuZhaLw5ybCw9dN
7iOiOoFexwJBANgYqhm0bQKWusSilD0mNmdq6HfSJsVOh5o/6GLsIEhPGkawAPkW
eReTr/Ucu+88a2QXo7GGjPRQxTY8UVcLl0cCQGO+nLbQJRtSYHgAlJstXbaEhxqs
ND/RdBOBjL2GXCjqSFPsr3542NhqxDxy7Thh5UOh+XR/oSXu1E7zvvBI9ZkCQECm
iGVuVFq8652eokj1ILuqAWivp8fJ6cndKtJFoJbhi5PwXionbgz+s1rawOMfKWXl
qKSZA5yoeYfzXcZ0AksCQQC3NtXZCOLRHvs+aawuUDyi0GmTNYgg3DNVP5vIUFRl
KyWKpbO+hG9eIqczRK4IxN89hoCD00GhRiWGqAVUGGhz
-----END RSA PRIVATE KEY-----"""

PRIVATEKEY = keyfactory.parsePrivateKey(PEM)


class _Signature(oauth.SignatureMethod):
    name = 'RSA-SHA1'

    def signing_base(self, request, consumer, token):
        if not hasattr(request, 'normalized_url') or request.normalized_url is None:
            raise ValueError("Base URL for request is not set.")

        sig = (
            oauth.escape(request.method),
            oauth.escape(request.normalized_url),
            oauth.escape(request.get_normalized_parameters()),
        )
        # ('POST',
        # 'http%3A%2F%2Flocalhost%3A7990%2Fplugins%2Fservlet%2Foauth%2Frequest-token',
        # 'oauth_consumer_key%3DjFzYB8pKJnz2BhaDUw%26oauth_nonce%3D15620364%26oauth_signature_method%3DRSA-SHA1%26oauth_timestamp%3D1442832674%26oauth_version%3D1.0')

        key = '%s&' % oauth.escape(consumer.secret)
        if token:
            key += oauth.escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def sign(self, request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.signing_base(request, consumer, token)

        signature = PRIVATEKEY.hashAndSign(raw)

        return base64.b64encode(signature)


signature = _Signature()


class BitbucketServer(BaseHandler):
    # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html
    service = 'bitbucket_server'
    service_url = os.getenv('BITBUCKET_SERVER_URL')
    urls = dict(user='users/%(username)s',
                owner='projects/%(username)s',
                repo='projects/%(username)s/repos/%(name)s',
                issues='projects/%(username)s/repos/%(name)s/issues/%(issueid)s',
                commit='projects/%(username)s/repos/%(name)s/commits/%(commitid)s',
                commits='projects/%(username)s/repos/%(name)s/commits',
                src='projects/%(username)s/repos/%(name)s/browse/%(path)s?at=%(commitid)s',
                tree='projects/%(username)s/repos/%(name)s/browse?at=%(commitid)s',
                create_file=None,
                branch='projects/%(username)s/repos/%(name)s/browser?at=%(branch)s',
                pull='projects/%(username)s/repos/%(name)s/pull-requests/%(pr)s/overview',
                compare='')

    @property
    def project(self):
        if self.data['owner'].get('service_id', '?')[0] == 'U':
            return '/projects/~%s' % self.data['owner']['username'].upper()
        else:
            return '/projects/%s' % self.data['owner']['username'].upper()

    def diff_to_json(self, diff_json):
        results = {}
        for _diff in diff_json:
            if not _diff.get('destination'):
                results[_diff['source']['toString']] = dict(type='deleted')

            else:
                fname = _diff['destination']['toString']
                _before = _diff['source']['toString'] if _diff.get('source') else None
                _file = results.setdefault(fname, dict(before=_before if _before != fname else None,
                                                       type='new' if _before is None else 'modified',
                                                       segments=[]))

                for hunk in _diff['hunks']:
                    segment = dict(header=[str(hunk['sourceLine']), str(hunk['sourceSpan']),
                                           str(hunk['destinationLine']), str(hunk['destinationSpan'])],
                                   lines=[])
                    _file['segments'].append(segment)
                    for seg in hunk['segments']:
                        t = seg['type'][0]
                        for l in seg['lines']:
                            segment['lines'].append(('-' if t == 'R' else '+' if t == 'A' else ' ') + l['line'])

        return self._add_diff_totals(dict(files=results)) if results else None

    @gen.coroutine
    def api(self, method, url, body=None, token=None, **kwargs):
        # process desired api path
        if not url.startswith('http'):
            url = '%s/rest/api/1.0%s' % (self.service_url, url)

        # process inline arguments
        if kwargs:
            url = url_concat(url, kwargs)

        # get accessing token
        if token:
            token = oauth.Token(token['key'], token['secret'])
        elif self.token:
            token = oauth.Token(self.token['key'], self.token['secret'])
        else:
            token = None

        # create oauth consumer
        if self.verify_ssl is False:
            # https://github.com/joestump/python-oauth2/blob/9d5a569fc9edda678102edccb330e1f692122a5a/oauth2/__init__.py#L627
            # https://github.com/jcgregorio/httplib2/blob/e7f6e622047107e701ee70e7ec586717d97b0cbb/python2/httplib2/__init__.py#L1158
            verify_ssl = dict(disable_ssl_certificate_validation=True, ca_certs=False)
        elif self.verify_ssl:
            verify_ssl = dict(ca_certs=self.verify_ssl)
        else:
            verify_ssl = dict(ca_certs=os.getenv('REQUESTS_CA_BUNDLE'))

        client = oauth.Client(oauth.Consumer(self._oauth_consumer_token()['key'], ''), token, **verify_ssl)
        client.set_signature_method(signature)

        response, content = client.request(url, method.upper(), dumps(body) if body else '',
                                           headers={'Content-Type': 'application/json'} if body else {})
        status = int(response['status'])

        if status in (200, 201):
            if 'application/json' in response.get('content-type'):
                raise gen.Return(loads(content))
            else:
                try:
                    content = dict(parse_qsl(content)) or content
                except:
                    pass

                raise gen.Return(content)

        elif status == 204:
            raise gen.Return(None)

        raise HTTPError(status)

    @gen.coroutine
    def get_authenticated(self, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp1889424
        if self.data['repo']['private']:
            yield self.api('get', '%s/repos/%s' % (self.project, self.data['repo']['name']), token=token)
        raise gen.Return((True, True))

    @gen.coroutine
    def get_is_admin(self, user, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3389568
        res = yield self.api('get', '%s/permissions/users' % self.project, filter=user['username'], token=token)
        userid = str(user['service_id']).replace('U', '')
        # PROJECT_READ, PROJECT_WRITE, PROJECT_ADMIN, ADMIMN
        res = any(filter(lambda v: str(v['user']['id']) == userid and 'ADMIN' in v['permission'], res['values']))
        raise gen.Return(res)

    @gen.coroutine
    def get_repository(self, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp1889424
        res = yield self.api('get', '%s/repos/%s' % (self.project, self.data['repo']['name']), token=token)
        owner_service_id = res['project']['id']
        if res['project']['type'] == 'PERSONAL':
            owner_service_id = 'U%d' % res['project']['owner']['id']

        fork = None
        if res.get('origin'):
            _fork_owner_service_id = res['origin']['project']['id']
            if res['origin']['project']['type'] == 'PERSONAL':
                _fork_owner_service_id = 'U%d' % res['origin']['project']['owner']['id']

            fork = dict(owner=dict(service_id=_fork_owner_service_id,
                                   username=res['origin']['project']['key']),
                        repo=dict(service_id=res['origin']['id'],
                                  language=None,
                                  private=(not res['origin']['public']),
                                  branch='master',
                                  name=res['origin']['slug']))

        raise gen.Return(dict(owner=dict(service_id=owner_service_id,
                                         username=res['project']['key']),
                              repo=dict(service_id=res['id'],
                                        language=None,
                                        private=(not res.get('public', res.get('origin', {}).get('public'))),
                                        branch='master',
                                        fork=fork,
                                        name=res['slug'])))

    @gen.coroutine
    def get_source(self, path, ref, token=None):
        content, start = [], 0
        while True:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2028128
            res = yield self.api('get', '%s/repos/%s/browse/%s' % (self.project, self.data['repo']['name'], path),
                                 at=ref, start=start, token=token)

            content.extend(res['lines'])
            if res['isLastPage'] or res.get('nextPageStart') is None:
                break
            else:
                start = res['nextPageStart']

        raise gen.Return(dict(commitid=None,  # [FUTURE] unknown atm
                              content='\n'.join(map(lambda a: a.get('text', ''), content))))

    @gen.coroutine
    def get_commit(self, commit, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3530560
        res = yield self.api('get', '%s/repos/%s/commits/%s' % (self.project, self.data['repo']['name'], commit),
                             token=token)

        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2598928
        _a = yield self.api('get', '/users', filter=res['author']['emailAddress'], token=token)
        if not _a['size']:
            _a = yield self.api('get', '/users', filter=res['author']['name'])
        author = _a['values'][0] if _a['size'] else {}

        raise gen.Return(dict(author=dict(id=('U%s' % author.get('id')) if author.get('id') else None,
                                          username=author.get('name'),
                                          email=res['author']['emailAddress'],
                                          name=res['author']['name']),
                              commitid=commit,
                              parents=[p['id'] for p in res['parents']],
                              message=res['message'],
                              timestamp=datetime.fromtimestamp(int(str(res['authorTimestamp'])[:10])).strftime('%Y-%m-%d %H:%M:%S')))

    @gen.coroutine
    def get_pull_request_commits(self, pullid, token=None):
        commits, start = [], 0
        while True:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2519392
            res = yield self.api('get', '%s/repos/%s/pull-requests/%s/commits' % (self.project, self.data['repo']['name'], pullid),
                                 start=start, token=token)
            if len(res['values']) == 0:
                break
            commits.extend([c['id'] for c in res['values']])
            if res['isLastPage'] or res.get('nextPageStart') is None:
                break
            else:
                start = res['nextPageStart']

        raise gen.Return(commits)

    @gen.coroutine
    def get_commit_diff(self, commit, context=None, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3120016
        diff = yield self.api('get', '%s/repos/%s/commits/%s/diff' % (self.project, self.data['repo']['name'], commit),
                              withComments=False,
                              whitespace='ignore-all',
                              contextLines=context or -1,
                              token=None)
        raise gen.Return(self.diff_to_json(diff['diffs']))

    @gen.coroutine
    def get_compare(self, base, head, context=None, with_commits=True, token=None):
        # get diff
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3370768
        diff = (yield self.api('get', '%s/repos/%s/commits/%s/diff' % (self.project, self.data['repo']['name'], head),
                               withComments=False,
                               whitespace='ignore-all',
                               contextLines=context or -1,
                               since=base,
                               token=token))['diffs']

        # get commits
        commits, start = [], 0
        while with_commits:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3358848
            # [TODO] what order are these commits? they need to be [latest....oldest]
            res = yield self.api('get', '%s/repos/%s/compare/commits' % (self.project, self.data['repo']['name']),
                                 start=start, limit=100, token=token, **{'from': base, 'to': head})
            commits.extend([dict(commitid=c['id'],
                                 message=c['message'],
                                 timestamp=c['authorTimestamp'],
                                 author=dict(name=c['author']['name'],
                                             email=c['author']['emailAddress'])) for c in res['values']])
            if res['isLastPage'] or res.get('nextPageStart') is None:
                break
            else:
                start = res['nextPageStart']

        raise gen.Return(dict(diff=self.diff_to_json(diff),
                              commits=commits))

    @gen.coroutine
    def get_pull_request(self, pullid, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2167824
        res = yield self.api('get', '%s/repos/%s/pull-requests/%s' % (self.project, self.data['repo']['name'], pullid),
                             token=token)
        # need to get all commits, shit.
        commits = yield self.get_pull_request_commits(pullid, token=token)
        raise gen.Return(dict(open=res['open'],
                              merged=res['state'] == 'MERGED',
                              id=str(pullid),
                              number=str(pullid),
                              base=dict(branch=res['toRef']['id'].replace('refs/heads/', ''),
                                        commitid=commits[-1]),
                              head=dict(branch=res['fromRef']['id'].replace('refs/heads/', ''),
                                        commitid=commits[0])))

    @gen.coroutine
    def list_repos(self, username=None, token=None):
        data, start = [], 0
        while True:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp1847760
            res = yield self.api('get', '/repos', start=start, token=token)
            if len(res['values']) == 0:
                break

            for repo in res['values']:
                ownerid = str(repo['project']['id'])
                if repo['project']['type'] == 'PERSONAL':
                    ownerid = 'U'+str(repo['project']['owner']['id'])

                fork = None
                if repo.get('origin'):
                    _fork_owner_service_id = str(repo['origin']['project']['id'])
                    if repo['origin']['project']['type'] == 'PERSONAL':
                        _fork_owner_service_id = 'U%d' % repo['origin']['project']['owner']['id']

                    fork = dict(owner=dict(service_id=_fork_owner_service_id,
                                           username=repo['origin']['project']['key']),
                                repo=dict(service_id=repo['origin']['id'],
                                          language=None,
                                          private=(not repo['origin']['public']),
                                          branch='master',
                                          name=repo['origin']['slug']))

                data.append(dict(owner=dict(service_id=ownerid,
                                            username=repo['project']['key'].lower().replace('~', '')),
                                 repo=dict(service_id=repo['id'],
                                           name=repo['slug'].lower(),
                                           language=None,
                                           private=(not repo.get('public', repo.get('origin', {}).get('public'))),
                                           branch='master',
                                           fork=fork)))
            if res['isLastPage'] or res.get('nextPageStart') is None:
                break
            else:
                start = res['nextPageStart']

        raise gen.Return(data)

    @gen.coroutine
    def list_teams(self, token=None):
        data, start = [], 0
        while True:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2301216
            res = yield self.api('get', '/projects', start=start, token=token)
            if len(res['values']) == 0:
                break
            data.extend([dict(id=row['id'], username=row['key'], name=row['name'])
                         for row in res['values']])
            if res['isLastPage'] or res.get('nextPageStart') is None:
                break
            else:
                start = res['nextPageStart']

        raise gen.Return(data)

    @gen.coroutine
    def get_commit_statuses(self, commit, _merge=None, token=None):
        # https://developer.atlassian.com/stash/docs/latest/how-tos/updating-build-status-for-commits.html
        start, data = 0, []
        while True:
            res = yield self.api('get', '%s/rest/build-status/1.0/commits/%s' % (self.service_url, commit),
                                 start=start, token=token)
            if len(res['values']) == 0:
                break
            data.extend([{'time': s['dateAdded'],
                          'state': s['state'],
                          'url': s['url'],
                          'context': s['name']} for s in res['values']])
            if res['isLastPage'] or res.get('nextPageStart') is None:
                break
            else:
                start = res['nextPageStart']

        raise gen.Return(Status(data))

    @gen.coroutine
    def set_commit_status(self, commit, status, context, description, url=None, token=None):
        # https://developer.atlassian.com/stash/docs/latest/how-tos/updating-build-status-for-commits.html
        assert status in ('pending', 'success', 'error', 'failure'), 'status not valid'
        yield self.api('post', '%s/rest/build-status/1.0/commits/%s' % (self.service_url, commit),
                       body=dict(state=dict(pending='INPROGRESS', success='SUCCESSFUL', error='FAILED', failure='FAILED').get(status),
                                 key=context,
                                 name=context,
                                 url=url,
                                 description=description),
                       token=token)
        raise gen.Return(True)

    @gen.coroutine
    def post_comment(self, issueid, body, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3165808
        res = yield self.api('post', '%s/repos/%s/pull-requests/%s/comments' % (self.project, self.data['repo']['name'], issueid),
                             body=dict(text=body), token=token)
        raise gen.Return('%(id)s:%(version)s' % res)

    @gen.coroutine
    def edit_comment(self, issueid, commentid, body, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3184624
        commentid, version = commentid.split(':', 1)
        res = yield self.api('put', '%s/repos/%s/pull-requests/%s/comments/%s' % (self.project, self.data['repo']['name'], issueid, commentid),
                             body=dict(text=body, version=version), token=token)
        raise gen.Return('%(id)s:%(version)s' % res)

    @gen.coroutine
    def delete_comment(self, issueid, commentid, token=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3189408
        commentid, version = commentid.split(':', 1)
        yield self.api('delete', '%s/repos/%s/pull-requests/%s/comments/%s' % (self.project, self.data['repo']['name'], issueid, commentid),
                       version=version, token=token)
        raise gen.Return(True)

    @gen.coroutine
    def get_branches(self, token=None):
        branches, start = [], 0
        while True:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2243696
            res = yield self.api('get', '%s/repos/%s/branches' % (self.project, self.data['repo']['name']),
                                 start=start, token=token)
            if len(res['values']) == 0:
                break
            branches.extend([(b['displayId'], b['latestCommit']) for b in res['values']])
            if res['isLastPage'] or res.get('nextPageStart') is None:
                break
            else:
                start = res['nextPageStart']
        raise gen.Return(branches)

    @gen.coroutine
    def get_pull_requests(self, commit=None, branch=None, state='open', token=None):
        prs, start = [], 0
        state = {'open': 'OPEN', 'close': 'DECLINED', 'merged': 'MERGED'}.get(state, 'ALL')
        while True:
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2048560
            res = yield self.api('get', '%s/repos/%s/pull-requests' % (self.project, self.data['repo']['name']),
                                 state=state,
                                 withAttributes=False,
                                 withProperties=False,
                                 start=start,
                                 token=token)
            if len(res['values']) == 0:
                break
            prs.extend([(None, str(b['id']))
                        for b in res['values']
                        if branch is None or branch == b['fromRef']['id'].replace('refs/heads/', '')])
            if res['isLastPage'] or res.get('nextPageStart') is None:
                break
            else:
                start = res['nextPageStart']
        raise gen.Return(prs)
