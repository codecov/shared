import os
from time import time
from sys import stdout
from json import loads
from json import dumps
from tornado import gen
import urllib as urllib_parse
from tornado.web import HTTPError
from tornado.auth import OAuthMixin
from tornado.httputil import url_concat
from requests_oauthlib import OAuth1Session
from tornado.httpclient import HTTPError as ClientError

from torngit.status import Status
from torngit.base import BaseHandler


class Bitbucket(BaseHandler, OAuthMixin):
    service = 'bitbucket'
    api_url = 'https://bitbucket.org'
    service_url = 'https://bitbucket.org'
    urls = dict(repo='%(username)s/%(name)s',
                owner='%(username)s',
                user='%(username)s',
                issues='%(username)s/%(name)s/issues/%(issueid)s',
                commit='%(username)s/%(name)s/commits/%(commitid)s',
                commits='%(username)s/%(name)s/commits',
                src='%(username)s/%(name)s/src/%(commitid)s/%(path)s',
                create_file='%(username)s/%(name)s/create-file/%(commitid)s?at=%(branch)s&filename=%(path)s&content=%(content)s',
                tree='%(username)s/%(name)s/src/%(commitid)s',
                branch='%(username)s/%(name)s/branch/%(branch)s',
                pull='%(username)s/%(name)s/pull-requests/%(pr)s',
                compare='%(username)s/%(name)s')

    @gen.coroutine
    def api(self, version, method, path, json=False, body=None, token=None, **kwargs):
        url = 'https://bitbucket.org/api/%s.0%s' % (version, path)
        headers = {'Accept': 'application/json',
                   'User-Agent': os.getenv('USER_AGENT', 'Default')}

        # make oauth request
        all_args = {}
        all_args.update(kwargs)
        if json:
            headers['Content-Type'] = 'application/json'
        else:
            all_args.update(body or {})
        oauth = self._oauth_request_parameters(url, token or self.token, all_args, method=method.upper())
        kwargs.update(oauth)

        url = url_concat(url, kwargs)
        kwargs = dict(method=method.upper(),
                      body=dumps(body) if json else urllib_parse.urlencode(body) if body else None,
                      ca_certs=self.verify_ssl if type(self.verify_ssl) is not bool else None,
                      validate_cert=self.verify_ssl if type(self.verify_ssl) is bool else None,
                      headers=headers,
                      connect_timeout=self._timeouts[0],
                      request_timeout=self._timeouts[1])

        start = time()
        try:
            res = yield self.fetch(url, **kwargs)

        except ClientError as e:
            if e.response is None:
                stdout.write('count#%s.timeout=1\n' % self.service)
                raise ClientError(502, 'Bitbucket was not able to be reached, server timed out.')

            else:
                self.log(url=url,
                         status=e.response.code,
                         endpoint=path,
                         body=e.response.body)
            e.message = 'Bitbucket API: %s' % e.message
            raise

        else:
            self.log(url=url, status=res.code, endpoint=path)
            if res.code == 204:
                raise gen.Return(None)

            elif 'application/json' in res.headers.get('Content-Type'):
                raise gen.Return(loads(res.body))

            else:
                raise gen.Return(res.body)

        finally:
            stdout.write("source=%s measure#service=%dms\n" % (self.service, int((time() - start) * 1000)))

    @gen.coroutine
    def _oauth_get_user_future(self, access_token):
        self.set_token(access_token)
        user = yield self.api('2', 'get', '/user')
        raise gen.Return(user)

    @gen.coroutine
    def post_webhook(self, name, url, events, secret, token=None):
        # https://confluence.atlassian.com/bitbucket/webhooks-resource-735642279.html
        # https://confluence.atlassian.com/bitbucket/event-payloads-740262817.html
        res = yield self.api('2', 'post', '/repositories/%s/hooks' % self.slug,
                             body=dict(description=name,
                                       active=True,
                                       events=events,
                                       url=url),
                             json=True,
                             token=token)
        raise gen.Return(res['uuid'][1:-1])

    @gen.coroutine
    def edit_webhook(self, hookid, name, url, events, secret, token=None):
        # https://confluence.atlassian.com/bitbucket/webhooks-resource-735642279.html#webhooksResource-PUTawebhookupdate
        yield self.api('2', 'put', '/repositories/%s/hooks/%s' % (self.slug, hookid),
                       body=dict(description=name,
                                 active=True,
                                 events=events,
                                 url=url),
                       json=True,
                       token=token)
        raise gen.Return(True)

    @gen.coroutine
    def delete_webhook(self, hookid, token=None):
        # https://confluence.atlassian.com/bitbucket/webhooks-resource-735642279.html#webhooksResource-DELETEthewebhook
        yield self.api('2', 'delete', '/repositories/%s/hooks/%s' % (self.slug, hookid), token=token)
        raise gen.Return(True)

    @gen.coroutine
    def get_is_admin(self, user, token=None):
        # https://confluence.atlassian.com/bitbucket/user-endpoint-296092264.html#userEndpoint-GETalistofuserprivileges
        res = yield self.api('1', 'get', '/user/privileges', token=token)
        raise gen.Return(res['teams'].get(self.data['owner']['username']) == 'admin')

    @gen.coroutine
    def list_teams(self, token=None):
        # https://confluence.atlassian.com/bitbucket/user-endpoint-296092264.html#userEndpoint-GETalistofuserprivileges
        res = yield self.api('1', 'get', '/user/privileges', token=token)
        data = []
        for username in res['teams'].keys():
            # https://confluence.atlassian.com/bitbucket/teams-endpoint-423626335.html#teamsEndpoint-GETtheteamprofile
            team = yield self.api('2', 'get', '/teams/%s' % username, token=token)
            data.append(dict(name=team['display_name'],
                             id=team['uuid'][1:-1],
                             email=None,
                             username=username))
        raise gen.Return(data)

    @gen.coroutine
    def get_pull_request_commits(self, pullid, token=None):
        commits, page = [], 0
        while True:
            page += 1
            # https://confluence.atlassian.com/bitbucket/pullrequests-resource-423626332.html#pullrequestsResource-GETthecommitsforapullrequest
            res = yield self.api('2', 'get', '/repositories/%s/pullrequests/%s/commits' % (self.slug, pullid),
                                 page=page, token=token)
            if len(res['values']) == 0:
                break
            commits.extend([c['hash'] for c in res['values']])
            if not res.get('next'):
                break

        raise gen.Return(commits)

    @gen.coroutine
    def list_repos(self, username=None, token=None):
        data, page = [], 0
        assert username, 'Must include username to list repos'
        while True:
            page += 1
            # https://confluence.atlassian.com/display/BITBUCKET/repositories+Endpoint#repositoriesEndpoint-GETalistofrepositoriesforanaccount
            res = yield self.api('2', 'get', '/repositories/%s' % (username or ''),
                                 page=page,
                                 token=token)
            if len(res['values']) == 0:
                break
            for repo in res['values']:
                data.append(dict(owner=dict(service_id=repo['owner']['uuid'][1:-1],
                                            username=repo['owner']['username']),
                                 repo=dict(service_id=repo['uuid'][1:-1],
                                           name=repo['full_name'].split('/', 1)[1],
                                           language=self._validate_language(repo['language']),
                                           private=repo['is_private'],
                                           branch='master',
                                           fork=None)))
            if not res.get('next'):
                break

        raise gen.Return(data)

    @gen.coroutine
    def get_pull_request(self, pullid, token=None):
        # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource#pullrequestsResource-GETaspecificpullrequest
        res = yield self.api('2', 'get', '/repositories/%s/pullrequests/%s' % (self.slug, pullid), token=token)
        # the commit sha is only {12}. need to get full sha
        base = yield self.api('2', 'get', '/repositories/%s/commit/%s' % (self.slug, res['destination']['commit']['hash']), token=token)
        head = yield self.api('2', 'get', '/repositories/%s/commit/%s' % (self.slug, res['source']['commit']['hash']), token=token)
        raise gen.Return(dict(base=dict(branch=res['destination']['branch']['name'],
                                        commitid=base['hash']),
                              head=dict(branch=res['source']['branch']['name'],
                                        commitid=head['hash']),
                              open=res['state'] == 'OPEN',
                              merged=res['state'] == 'MERGED',
                              title=res['title'],
                              id=str(pullid),
                              number=str(pullid)))

    @gen.coroutine
    def post_comment(self, issueid, body, token=None):
        # https://confluence.atlassian.com/display/BITBUCKET/issues+Resource#issuesResource-POSTanewcommentontheissue
        res = yield self.api('1', 'post', '/repositories/%s/pullrequests/%s/comments' % (self.slug, issueid),
                             body=dict(content=body), token=token)
        raise gen.Return(res['comment_id'])

    @gen.coroutine
    def edit_comment(self, issueid, commentid, body, token=None):
        # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource+1.0#pullrequestsResource1.0-PUTanupdateonacomment
        # yield self.api('1', 'put', '/repositories/%s/pullrequests/%s/comments/%s' % (self.slug, issueid, commentid),
        #                body=dict(content=body), token=token)
        client = self._oauth_consumer_token()
        token = (token or self.token)
        url = 'https://bitbucket.org/api/1.0/repositories/%s/pullrequests/%s/comments/%s' % (self.slug, issueid, commentid)
        oauth = OAuth1Session(client['key'], client_secret=client['secret'],
                              resource_owner_key=token['key'],
                              resource_owner_secret=token['secret'])
        res = oauth.put(url, data=dict(content=body))
        assert res.status_code == 200
        raise gen.Return(commentid)

    @gen.coroutine
    def delete_comment(self, issueid, commentid, token=None):
        # https://confluence.atlassian.com/bitbucket/pullrequests-resource-1-0-296095210.html#pullrequestsResource1.0-PUTanupdateonacomment
        yield self.api('1', 'delete', '/repositories/%s/pullrequests/%s/comments/%s' % (self.slug, issueid, commentid),
                       token=token)
        raise gen.Return(True)

    @gen.coroutine
    def get_commit_status(self, commit, token=None):
        # https://confluence.atlassian.com/bitbucket/buildstatus-resource-779295267.html
        statuses = yield self.get_commit_statuses(commit, token=token)
        raise gen.Return(str(statuses))

    @gen.coroutine
    def get_commit_statuses(self, commit, token=None):
        statuses, page = [], 0
        status_keys = dict(INPROGRESS='pending', SUCCESSFUL='success', FAILED='failure')
        while True:
            page += 1
            # https://api.bitbucket.org/2.0/repositories/atlassian/aui/commit/d62ae57/statuses
            res = yield self.api('2', 'get', '/repositories/%s/commit/%s/statuses' % (self.slug, commit),
                                 page=page, token=token)
            _statuses = res['values']
            if len(_statuses) == 0:
                break
            statuses.extend([{'time': s['updated_on'],
                              'state': status_keys.get(s['state']),
                              'url': s['url'],
                              'context': s['key']} for s in _statuses])
            if not res.get('next'):
                break
        raise gen.Return(Status(statuses))

    @gen.coroutine
    def set_commit_status(self, commit, status, context, description, url, merge_commit=None, token=None):
        # https://confluence.atlassian.com/bitbucket/buildstatus-resource-779295267.html
        status = dict(pending='INPROGRESS', success='SUCCESSFUL', error='FAILED', failure='FAILED').get(status)
        assert status, 'status not valid'
        try:
            res = yield self.api('2', 'post', '/repositories/%s/commit/%s/statuses/build' % (self.slug, commit),
                                 body=dict(state=status,
                                           key='codecov-'+context,
                                           name=context.replace('/', ' ').capitalize()+' Coverage',
                                           url=url,
                                           description=description),
                                 token=token)
        except:
            res = yield self.api('2', 'put', '/repositories/%s/commit/%s/statuses/build/codecov-%s' % (self.slug, commit, context),
                                 body=dict(state=status,
                                           name=context.replace('/', ' ').capitalize()+' Coverage',
                                           url=url,
                                           description=description),
                                 token=token)

        if merge_commit:
            try:
                res = yield self.api('2', 'post', '/repositories/%s/commit/%s/statuses/build' % (self.slug, merge_commit[0]),
                                     body=dict(state=status,
                                               key='codecov-'+merge_commit[1],
                                               name=merge_commit[1].replace('/', ' ').capitalize()+' Coverage',
                                               url=url,
                                               description=description),
                                     token=token)
            except:
                res = yield self.api('2', 'put', '/repositories/%s/commit/%s/statuses/build/codecov-%s' % (self.slug, merge_commit[0], context),
                                     body=dict(state=status,
                                               name=merge_commit[1].replace('/', ' ').capitalize()+' Coverage',
                                               url=url,
                                               description=description),
                                     token=token)
        # check if the commit is a Merge
        raise gen.Return(res)

    @gen.coroutine
    def get_commit(self, commit, token=None):
        # https://confluence.atlassian.com/display/BITBUCKET/commits+or+commit+Resource#commitsorcommitResource-GETanindividualcommit
        data = yield self.api('2', 'get', '/repositories/%s/commit/%s' % (self.slug, commit), token=token)
        author_login = data['author'].get('user', {}).get('username')
        author_raw = data['author'].get('raw', '')[:-1].rsplit(' <', 1) if ' <' in data['author']['raw'] else None
        if author_login:
            # https://confluence.atlassian.com/display/BITBUCKET/users+Endpoint#usersEndpoint-GETtheuserprofile
            res = yield self.api('2', 'get', '/users/%s' % author_login, token=token)
            userid = res['uuid'][1:-1]
        else:
            userid = None

        raise gen.Return(dict(author=dict(id=userid,
                                          username=author_login,
                                          name=author_raw[0] if author_raw else None,
                                          email=author_raw[1] if author_raw else None),
                              commitid=commit,
                              parents=[p['hash'] for p in data['parents']],
                              message=data['message'],
                              timestamp=data['date']))

    @gen.coroutine
    def get_branches(self, token=None):
        # https://confluence.atlassian.com/display/BITBUCKET/repository+Resource+1.0#repositoryResource1.0-GETlistofbranches
        res = yield self.api('1', 'get', '/repositories/%s/branches' % self.slug, token=token)
        raise gen.Return([(k, b['raw_node']) for k, b in res.iteritems()])

    @gen.coroutine
    def get_pull_requests(self, commit=None, branch=None, state='open', token=None):
        state = {'open': 'OPEN', 'merged': 'MERGED', 'close': 'DECLINED'}.get(state, '')
        pulls, page = [], 0
        while True:
            page += 1
            # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource#pullrequestsResource-GETalistofopenpullrequests
            res = yield self.api('2', 'get', '/repositories/%s/pullrequests' % self.slug,
                                 state=state, page=page, token=token)
            _prs = res['values']
            if len(_prs) == 0:
                break

            if commit:
                for b in _prs:
                    if commit.startswith(b['source']['commit']['hash']):
                        raise gen.Return([(None, str(b['id']))])
            else:
                pulls.extend([(None, str(b['id']))
                              for b in _prs
                              if branch is None or b['source']['branch']['name'] == branch])
            if not res.get('next'):
                break

        if commit:
            raise gen.Return(None)
        else:
            raise gen.Return(pulls)

    @gen.coroutine
    def get_repository(self, token=None):
        if self.data['repo'].get('service_id') is None:
            # https://confluence.atlassian.com/display/BITBUCKET/repository+Resource#repositoryResource-GETarepository
            res = yield self.api('2', 'get', '/repositories/'+self.slug, token=token)
        else:
            res = yield self.api('2', 'get', '/repositories/%%7B%s%%7D/%%7B%s%%7D' % (self.data['owner']['service_id'], self.data['repo']['service_id']),
                                 token=token)
        username, repo = tuple(res['full_name'].split('/', 1))
        raise gen.Return(dict(owner=dict(service_id=res['owner']['uuid'][1:-1],
                                         username=username),
                              repo=dict(service_id=res['uuid'][1:-1],
                                        private=res['is_private'],
                                        branch='master',
                                        language=self._validate_language(res['language']),
                                        name=repo)))

    @gen.coroutine
    def get_authenticated(self, token=None):
        if self.data['repo']['private']:
            # https://confluence.atlassian.com/bitbucket/repository-resource-423626331.html#repositoryResource-GETarepository
            yield self.api('2', 'get', '/repositories/'+self.slug, token=token)
            raise gen.Return((True, True))
        else:
            # https://confluence.atlassian.com/bitbucket/user-endpoint-296092264.html#userEndpoint-GETalistofuserprivileges
            groups = yield self.api('1', 'get', '/user/privileges', token=token)
            raise gen.Return((True, self.data['owner']['username'] in groups['teams']))

    @gen.coroutine
    def get_source(self, path, ref, token=None):
        # https://confluence.atlassian.com/bitbucket/src-resources-296095214.html
        src = yield self.api('1', 'get', '/repositories/%s/src/%s/%s' % (self.slug, ref, path),
                             token=token)
        raise gen.Return(dict(commitid=src['node'],
                              content=src['data']))

    @gen.coroutine
    def get_compare(self, base, head, context=None, with_commits=True, token=None):
        # https://developer.atlassian.com/bitbucket/api/2/reference/resource/snippets/%7Busername%7D/%7Bencoded_id%7D/%7Brevision%7D/diff%C2%A0%E2%80%A6
        # https://api.bitbucket.org/2.0/repositories/markadams-atl/test-repo/diff/1b03803..fcba34b
        # IMPORANT it is reversed
        diff = yield self.api('2', 'get', '/repositories/%s/diff/%s..%s' % (self.slug, head, base),
                              context=context or 0,
                              token=token)

        commits = []
        if with_commits:
            page = 0
            while page > -1:
                page += 1
                # https://api.bitbucket.org/2.0/repositories/markadams-atl/test-repo/commits/fcba34b
                res = yield self.api('2', 'get', '/repositories/%s/commits/%s' % (self.slug, head),
                                     page=page, token=token)

                if len(res['values']) == 0:
                    break

                for commit in res['values']:
                    try:
                        author = dict(id=commit['author']['user']['uuid'][1:-1],
                                      username=commit['author']['user']['username'],
                                      name=commit['author']['user']['name'])
                    except:
                        author = {}

                    commits.append(dict(commitid=commit['hash'],
                                        message=commit['message'],
                                        timestamp=commit['date'],
                                        author=author))

                    if commit['hash'].startswith(base):
                        page = -1
                        break

                if len(res['values']) < res['pagelen']:
                    break

        raise gen.Return(dict(diff=self.diff_to_json(diff),
                              commits=commits))

    @gen.coroutine
    def get_commit_diff(self, commit, context=None, token=None):
        # https://confluence.atlassian.com/bitbucket/diff-resource-425462484.html
        diff = yield self.api('2', 'get', '/repositories/'+self.data['owner']['username']+'/'+self.data['repo']['name']+'/diff/'+commit,
                              token=token)
        raise gen.Return(self.diff_to_json(diff))
