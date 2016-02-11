import os
import base64
import oauth2 as oauth
from json import loads
from tornado import gen
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
    icon = 'fa-bitbucket'
    urls = dict(owner='projects/%(username)s',
                repo='projects/%(username)s/repos/%(name)s',
                commit='projects/%(username)s/repos/%(name)s/commits/%(commitid)s',
                commits='projects/%(username)s/repos/%(name)s/commits',
                blob='projects/%(username)s/repos/%(name)s/browse/%(path)s?at=%(commitid)s',
                tree='projects/%(username)s/repos/%(name)s/browse?at=%(commitid)s',
                branch='projects/%(username)s/repos/%(name)s/browser?at=%(branch)s',
                pr='projects/%(username)s/repos/%(name)s/pull-requests/%(pr)s/overview',
                compare='')

    if os.getenv('BITBUCKET_SERVER_VERIFY_SSL') == 'FALSE':
        # https://github.com/joestump/python-oauth2/blob/9d5a569fc9edda678102edccb330e1f692122a5a/oauth2/__init__.py#L627
        # https://github.com/jcgregorio/httplib2/blob/e7f6e622047107e701ee70e7ec586717d97b0cbb/python2/httplib2/__init__.py#L1158
        verify_ssl = dict(disable_ssl_certificate_validation=True, ca_certs=False)

    elif os.getenv('BITBUCKET_SERVER_SSL_PEM'):
        verify_ssl = dict(ca_certs=os.getenv('BITBUCKET_SERVER_SSL_PEM'))

    else:
        verify_ssl = dict(ca_certs=os.getenv('REQUESTS_CA_BUNDLE'))

    @property
    def project(self):
        if str(self['owner_service_id'])[0] == 'U':
            return '/project/~'+self['username'].upper()
        else:
            return '/project/'+self['username'].upper()

    def diff_to_json(self, diff_json):
        results = {}
        for _diff in diff_json['diffs']:
            if not _diff['destination']:
                results[_diff['source']['toString']] = dict(type='deleted')

            else:
                fname = _diff['destination']['toString']
                _before = _diff['source']['toString'] if _diff['source'] else None
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

        return dict(files=results)

    @gen.coroutine
    def api(self, method, url, body=None, **kwargs):
        # process desired api path
        if not url.startswith('http'):
            url = self.service_url+'/rest/api/1.0'+url

        # process inline arguments
        if kwargs:
            url = url_concat(url, kwargs)

        # get accessing token
        token = oauth.Token(self.token['key'], self.token['secret']) if self.token else None

        # create oauth consumer
        client = oauth.Client(oauth.Consumer(self._oauth_consumer_token()['key'], ''), token, **self.verify_ssl)
        client.set_signature_method(signature)

        response, content = client.request(url, method.upper(), body or '')
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
    def get_authenticated(self):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp1889424
        if self['private']:
            yield self.api('get', self.project+'/repos/'+self['repo']['name'])
        raise gen.Return((True, True))

    @gen.coroutine
    def get_repository(self):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp1889424
        res = yield self.api('get', self.project+'/repos/'+self['repo']['name'])
        owner_service_id = res['project']['id']
        if res['project']['type'] == 'PERSONAL':
            owner_service_id = 'U%d' % res['project']['owner']['id']

        fork = None
        if res['origin']:
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
    def get_source(self, path, ref):
        content, page = [], 0
        while True:
            page += 1
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2028128
            res = yield self.api('get', self.project+'/repos/'+self['repo']['name']+'/browser/'+path,
                                 at=ref, page=page)
            content.extend(res['lines'])
            if res['isLastPage']:
                break

        raise gen.Return(dict(commitid=None,  # [TODO] unknown atm
                              content='\n'.join(map(lambda a: a.get('text', ''), content))))

    @gen.coroutine
    def get_commit(self, commitid):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3530560
        res = yield self.api('get', self.project+'/repos/'+self['repo']['name']+'/commits/'+commitid)

        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2598928
        _a = yield self.api('get', '/users', filter=res['author']['emailAddress'])
        if not _a['size']:
            _a = yield self.api('get', '/users', filter=res['author']['name'])
        author = _a['values'][0] if _a['size'] else {}

        raise gen.Return(dict(author=dict(id=author.get('id'),
                                          username=author.get('name'),
                                          email=res['author']['emailAddress'],
                                          name=res['author']['name']),
                              commitid=commitid,
                              message=res['message'],
                              date=res['authorTimestamp']))

    @gen.coroutine
    def get_pull_request_commits(self, pullid):
        commits, page = [], 0
        while True:
            page += 1
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2519392
            res = yield self.api('get', self.project+'/repos/'+self['repo']['name']+'/pull-requests/'+str(pullid),
                                 page=page)
            commits.extend([c['id'] for c in res['values']])
            if res['isLastPage']:
                break

        raise gen.Return(commits)

    @gen.coroutine
    def get_commit_diff(self, commitid, context=None):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3120016
        diff = yield self.api('get', self.project+'/repos/'+self['repo']['name']+'/commits/'+commitid+'/diff',
                              withComments=False,
                              whitespace='ignore-all',
                              contextLines=context or -1)
        raise gen.Return(self.diff_to_json(diff['diffs']))

    @gen.coroutine
    def get_compare(self, base, head, context=None, with_commits=True):
        # get diff
        diff, page = [], 0
        while True:
            page += 1
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3370768
            res = yield self.api('get', self.projects+'/repos/'+self['repo']['name']+'/commits/'+head+'/diff',
                                 page=page,
                                 withComments=False,
                                 whitespace='ignore-all',
                                 contextLines=context or -1,
                                 since=base)
            diff.extend(res['diffs'])
            if res['isLastPage']:
                break

        # get commits
        commits, page = [], 0
        while with_commits:
            page += 1
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3358848
            res = yield self.api('get', self.projects+'/repos/'+self['repo']['name']+'/compare/commits',
                                 page=page, **{'from': base, 'to': head})
            commits.extend([dict(commitid=c['id'],
                                 message=c['message'],
                                 date=c['authorTimestamp'],
                                 author=dict(name=c['author']['name'],
                                             email=c['author']['emailAddress'])) for c in res['values']])
            if res['isLastPage']:
                break

        raise gen.Return(dict(diff=self.diff_to_json(diff),
                              commits=commits))

    @gen.coroutine
    def get_pull_request(self, pr):
        # [TODO] figure out how to get base and head commitsids
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2167824
        res = yield self.api('get', self.project+'/repos/'+self['repo']['name']+'/pull-requests/'+str(pr))
        raise gen.Return(dict(open=res['open'],
                              merged=res['state'] == 'MERGED',
                              id=str(pr),
                              number=str(pr),
                              base=dict(branch=res['toRef']['id'].replace('refs/heads/', ''),
                                        commitid=None),
                              head=dict(branch=res['fromRef']['id'].replace('refs/heads/', ''),
                                        commitid=None)))

    @gen.coroutine
    def list_repos(self):
        data, page = [], 0
        while True:
            page += 1
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp1847760
            res = yield self.api('get', '/repos')
            for repo in res['values']:
                ownerid = repo['project']['id']
                if repo['project']['type'] == 'PERSONAL':
                    ownerid = 'U'+str(repo['project']['owner']['id'])

                fork = None
                if repo['origin']:
                    _fork_owner_service_id = repo['origin']['project']['id']
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
            if res['isLastPage']:
                break

        raise gen.Return(data)

    @gen.coroutine
    def get_commit_status(self, commit, _merge=None):
        # https://developer.atlassian.com/stash/docs/latest/how-tos/updating-build-status-for-commits.html
        page, data = 0, []
        while True:
            page += 1
            res = yield self.api('get', self.service_url+'/rest/build-status/1.0/commits/'+commit, page=page)
            data.extend([{'time': s['dateAdded'],
                          'state': s['state'],
                          'url': s['url'],
                          'context': s['name']} for s in res['values']])
            if res['isLastPage']:
                break

        raise gen.Return(Status(data))

    @gen.coroutine
    def set_commit_status(self, commitid, status, context, description, url=None):
        # https://developer.atlassian.com/stash/docs/latest/how-tos/updating-build-status-for-commits.html
        assert status in ('pending', 'success', 'error', 'failure'), 'status not valid'
        yield self.api('post', self.service_url+'/rest/build-status/1.0/commits/'+commitid,
                       body=dict(state=dict(pending='INPROGRESS', success='SUCCESSFUL', error='FAILED', failure='FAILED').get(status),
                                 key=context,
                                 name=context,
                                 url=url,
                                 description=description))
        raise gen.Return(True)

    @gen.coroutine
    def post_comment(self, issueid, body):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3165808
        res = yield self.api('post', '%s/repos/%s/pull-requests/%s/comments' % (self.project, self['repo']['name'], issueid),
                             body=dict(text=body))
        raise gen.Return(str(res['id'])+':'+str(res['version']))

    @gen.coroutine
    def edit_comment(self, issueid, commentid, body):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3184624
        commentid, version = commentid.split(':', 2)
        res = yield self.api('put', '%s/repos/%s/pull-requests/%s/comments/%s' % (self.project, self['repo']['name'], issueid, commentid),
                             body=dict(text=body, version=version))
        raise gen.Return(str(res['id'])+':'+str(res['version']))

    @gen.coroutine
    def delete_comment(self, issueid, commentid):
        # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp3189408
        commentid, version = commentid.split(':', 2)
        yield self.api('delete', '%s/repos/%s/pull-requests/%s/comments/%s' % (self.project, self['repo']['name'], issueid, commentid),
                       version=version)
        raise gen.Return(True)

    @gen.coroutine
    def get_branches(self):
        branches, page = [], 0
        while True:
            page += 1
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2243696
            res = yield self.api('get', self.project+'/repos/'+self['repo']['name']+'/branches', page=page)
            branches.extend([(b['displayId'], b['latestCommit']) for b in res['values']])
            if res['isLastPage']:
                break
        raise gen.Return(branches)

    @gen.coroutine
    def get_pull_requests(self, commitid=None, branch=None, state='open'):
        if commitid:
            raise NotImplemented('dont know how to search by commitid yet')

        prs, page = [], 0
        state = {'open': 'OPEN', 'close': 'DECLINED', 'merged': 'MERGED'}.get(state, 'ALL')
        while True:
            page += 1
            # https://developer.atlassian.com/static/rest/bitbucket-server/4.0.1/bitbucket-rest.html#idp2048560
            res = yield self.api('get', self.project+'/repos/'+self['repo']['name']+'/pull-requests',
                                 page=page,
                                 withAttributes=False,
                                 withProperties=False,
                                 state=state)
            prs.extend([str(b['id'])
                        for b in res['values']
                        if branch is None or branch == b['fromRef']['id'].replace('refs/heads/', '')])
            if res['isLastPage']:
                break
        raise gen.Return(prs)
