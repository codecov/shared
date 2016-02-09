import os
from json import loads
from tornado import gen
import urllib as urllib_parse
from tornado.web import HTTPError
from tornado.auth import OAuthMixin
from tornado.httputil import url_concat

from torngit.base import BaseHandler


class Bitbucket(BaseHandler, OAuthMixin):
    service = 'bitbucket'
    icon = 'fa-bitbucket'
    api_url = 'https://bitbucket.org'
    service_url = 'https://bitbucket.org'

    urls = dict(repo='%(username)s/%(repo)s',
                owner='%(username)s',
                commit='%(username)s/%(repo)s/commits/%(commitid)s',
                commits='%(username)s/%(repo)s/commits',
                blob='%(username)s/%(repo)s/src/%(commitid)s/%(path)s',
                tree='%(username)s/%(repo)s/src/%(commitid)s',
                branch='%(username)s/%(repo)s/branch/%(branch)s',
                pr='%(username)s/%(repo)s/pull-requests/%(pr)s',
                compare='%(username)s/%(repo)s')

    @gen.coroutine
    def api(self, version, method, path, body=None, **kwargs):
        url = 'https://bitbucket.org/api/%s.0%s' % (version, path)

        # make oauth request
        all_args = {}
        all_args.update(kwargs)
        all_args.update(body or {})
        oauth = self._oauth_request_parameters(url, self.token, all_args, method=method.upper())
        kwargs.update(oauth)

        res = yield self.fetch(url_concat(url, kwargs),
                               method=method.upper(),
                               body=urllib_parse.urlencode(body) if body else None,
                               headers={'Accept': 'application/json',
                                        'User-Agent': os.getenv('USER_AGENT', 'Default')},
                               connect_timeout=self.timeouts[0],
                               request_timeout=self.timeouts[1])

        if res.code == 204:
            raise gen.Return(None)

        elif 'application/json' in res.headers.get('Content-Type'):
            raise gen.Return(loads(res.body))

        else:
            raise gen.Return(res.body)

    @gen.coroutine
    def _oauth_get_user_future(self, access_token):
        self.set_token(access_token)
        user = yield self.api('2', 'get', '/user')
        raise gen.Return(user)

    @gen.coroutine
    def post_webhook(self, name, url, events, secret):
        # https://confluence.atlassian.com/bitbucket/webhooks-resource-735642279.html
        # https://confluence.atlassian.com/bitbucket/event-payloads-740262817.html
        res = yield self.api('2', 'post', '/repositories/'+self.slug+'/hooks',
                             body=dict(description=name,
                                       active=True,
                                       events=events,
                                       url=url))
        raise gen.Return(res['uuid'][1:-1])

    @gen.coroutine
    def edit_webhook(self, hookid, name, url, events, secret):
        # https://confluence.atlassian.com/bitbucket/webhooks-resource-735642279.html#webhooksResource-PUTawebhookupdate
        yield self.api('2', 'put', '/repositories/'+self.slug+'/hooks/'+hookid,
                       body=dict(description=name,
                                 active=True,
                                 events=events,
                                 url=url))
        raise gen.Return(True)

    @gen.coroutine
    def get_is_admin(self, username):
        # https://confluence.atlassian.com/bitbucket/user-endpoint-296092264.html#userEndpoint-GETalistofuserprivileges
        res = yield self.api('1', 'get', '/user/privileges')
        raise gen.Return(res['teams'].get(username) == 'admin')

    @gen.coroutine
    def list_teams(self):
        # https://confluence.atlassian.com/bitbucket/user-endpoint-296092264.html#userEndpoint-GETalistofuserprivileges
        res = yield self.api('1', 'get', '/user/privileges')
        data = []
        for username in res['teams'].keys():
            # https://confluence.atlassian.com/bitbucket/teams-endpoint-423626335.html#teamsEndpoint-GETtheteamprofile
            team = yield self.api('2', 'get', '/team/'+username)
            data.append(dict(name=team['display_name'],
                             id=team['uuid'][1:-1],
                             email=None,
                             username=username))
        raise gen.Return(data)

    @gen.coroutine
    def get_pull_request_commits(self, pullid):
        commits, page = [], 0
        while True:
            page += 1
            # https://confluence.atlassian.com/bitbucket/pullrequests-resource-423626332.html#pullrequestsResource-GETthecommitsforapullrequest
            res = yield self.api('2', 'get', '/repositories/%s/pullrequests/%s/commits' % (self.slug, pullid),
                                 page=page)
            commits.extend([c['hash'] for c in res['values']])
            if not res.get('next'):
                break

        raise gen.Return(commits)

    @gen.coroutine
    def list_repos(self):
        data, page = [], 0
        while True:
            page += 1
            # https://confluence.atlassian.com/display/BITBUCKET/repositories+Endpoint#repositoriesEndpoint-GETalistofrepositoriesforanaccount
            res = yield self.api('2', 'get', '/repositories', page=page)
            repos = res
            for repo in repos['values']:
                data.append(dict(owner=dict(service_id=repo['owner']['uuid'][1:-1],
                                            username=repo['owner']['username']),
                                 repo=dict(service_id=repo['uuid'][1:-1],
                                           name=repo['full_name'].split('/', 1)[1],
                                           language=repo['language'],
                                           private=repo['is_private'],
                                           branch='master',
                                           fork=None)))

            if not repos.get('next'):
                break

        raise gen.Return(data)

    @gen.coroutine
    def get_pull_request(self, pr):
        # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource#pullrequestsResource-GETaspecificpullrequest
        res = yield self.api('2', 'get', '/repositories/%s/pullrequests/%s' % (self.slug, pr))
        raise gen.Return(dict(base=dict(branch=res['destination']['branch']['name'],
                                        commitid=res['destination']['commit']['hash']),  # its only 12 long...ugh
                              head=dict(branch=res['source']['branch']['name'],
                                        commitid=res['source']['commit']['hash']),
                              open=res['state'] == 'OPEN',
                              merged=res['state'] == 'MERGED',
                              title=res['title'],
                              id=str(res['id']),
                              number=str(pr)))

    @gen.coroutine
    def post_comment(self, issueid, body):
        # https://confluence.atlassian.com/display/BITBUCKET/issues+Resource#issuesResource-POSTanewcommentontheissue
        res = yield self.api('1', 'post', '/repositories/%s/pullrequests/%s/comments' % (self.slug, issueid),
                             body=dict(content=body))
        raise gen.Return(res['comment_id'])

    @gen.coroutine
    def edit_comment(self, issueid, commentid, body):
        # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource+1.0#pullrequestsResource1.0-PUTanupdateonacomment
        yield self.api('1', 'put', '/repositories/%s/pullrequests/%s/comments/%s' % (self.slug, issueid, commentid),
                       body=dict(content=body))
        raise gen.Return(True)

    @gen.coroutine
    def delete_comment(self, issueid, commentid, body):
        # https://confluence.atlassian.com/bitbucket/pullrequests-resource-1-0-296095210.html#pullrequestsResource1.0-PUTanupdateonacomment
        yield self.api('1', 'delete', '/repositories/%s/pullrequests/%s/comments/%s' % (self.slug, issueid, commentid))
        raise gen.Return(True)

    @gen.coroutine
    def get_commit_status(self, commitid):
        # https://confluence.atlassian.com/bitbucket/buildstatus-resource-779295267.html
        # Cannot get "all" builds only lookup by vendor
        raise gen.Return(None)

    @gen.coroutine
    def set_commit_status(self, commitid, status, context, description, url):
        # https://confluence.atlassian.com/bitbucket/buildstatus-resource-779295267.html
        status = dict(pending='INPROGRESS', success='SUCCESSFUL', error='FAILED', failure='FAILED').get(status)
        assert status, 'status not valid'
        try:
            res = yield self.api('2', 'post', '/repositories/%s/commit/%s/statuses/build' % (self.slug, commitid),
                                 body=dict(state=status,
                                           key='codecov-'+context,
                                           name=context.capitalize()+' Coverage',
                                           url=url,
                                           description=description))
        except:
            res = yield self.api('2', 'put', '/repositories/%s/commit/%s/statuses/build/codecov-%s' % (self.slug, commitid, context),
                                 body=dict(state=status,
                                           name=context.capitalize()+' Coverage',
                                           url=url,
                                           description=description))

        # check if the commit is a Merge
        raise gen.Return(res)

    @gen.coroutine
    def get_commit(self, commitid):
        # https://confluence.atlassian.com/display/BITBUCKET/commits+or+commit+Resource#commitsorcommitResource-GETanindividualcommit
        data = yield self.api('2', 'get', '/repositories/'+self.slug+'/commit/'+commitid)
        author_login = data['author'].get('user', {}).get('username')
        author_raw = data['author']['raw'][:-1].rsplit(' <', 1)
        if author_login:
            # https://confluence.atlassian.com/display/BITBUCKET/users+Endpoint#usersEndpoint-GETtheuserprofile
            res = yield self.api('2', 'get', '/users/'+author_login)
            userid = res['uuid'][1:-1]
        else:
            userid = None

        raise gen.Return(dict(author=dict(id=userid,
                                          username=author_login,
                                          name=author_raw[0],
                                          email=author_raw[1]),
                              commitid=commitid,
                              message=data['message'],
                              date=data['date']))

    @gen.coroutine
    def get_branches(self):
        # https://confluence.atlassian.com/display/BITBUCKET/repository+Resource+1.0#repositoryResource1.0-GETlistofbranches
        res = yield self.api('1', 'get', '/repositories/'+self.slug+'/branches')
        raise gen.Return([(k, b['raw_node']) for k, b in res.iteritems()])

    @gen.coroutine
    def get_pull_requests(self, commitid=None, branch=None, state='open'):
        if commitid:
            raise NotImplemented('dont know how to search by commitid yet')

        state = {'open': 'OPEN', 'merged': 'MERGED', 'close': 'DECLINED'}.get(state, '')
        pulls, page = [], 0
        while True:
            page += 1
            # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource#pullrequestsResource-GETalistofopenpullrequests
            res = yield self.api('2', 'get', '/repositories/'+self.slug+'/pullrequests',
                                 state=state, page=page)
            _prs = res['values']
            if len(_prs) == 0:
                break
            pulls.extend([str(b['id'])
                          for b in _prs
                          if branch is None or b['source']['branch']['name'] == branch])
            if len(_prs) < 100:
                break
        raise gen.Return(pulls)

    @gen.coroutine
    def get_repository(self):
        if self['repo']['service_id'] is None:
            # https://confluence.atlassian.com/display/BITBUCKET/repository+Resource#repositoryResource-GETarepository
            res = yield self.api('2', 'get', '/repositories/'+self.slug)
        else:
            res = yield self.api('2', 'get', '/repositories/%%7B%s%%7D/%%7B%s%%7D' % (self['owner']['service_id'], self['repo']['service_id']))
        username, repo = tuple(res['full_name'].split('/', 1))
        raise gen.Return(dict(owner=dict(service_id=res['owner']['uuid'][1:-1],
                                         username=username),
                              repo=dict(service_id=res['uuid'][1:-1],
                                        private=res['is_private'],
                                        branch='master',
                                        name=repo)))

    @gen.coroutine
    def get_authenticated(self):
        if self['repo']['private']:
            # https://confluence.atlassian.com/bitbucket/repository-resource-423626331.html#repositoryResource-GETarepository
            yield self.api('2', 'get', '/repositories/'+self.slug)
            raise gen.Return((True, True))
        else:
            # https://confluence.atlassian.com/bitbucket/user-endpoint-296092264.html#userEndpoint-GETalistofuserprivileges
            groups = yield self.api('1', 'get', '/user/privileges')
            raise gen.Return((True, self['owner']['username'] in groups['teams']))

    @gen.coroutine
    def get_source(self, path, ref):
        # https://confluence.atlassian.com/bitbucket/src-resources-296095214.html
        src = yield self.api('1', 'get', '/repositories/'+self.slug+'/src/'+ref+'/'+path)
        raise gen.Return(dict(commitid=src['node'],
                              content=src['content']))

    @gen.coroutine
    def get_compare(self, base, head, context=None, with_commits=True):
        # https://bitbucket.org/site/master/issues/4779/ability-to-diff-between-any-two-commits
        raise HTTPError(501, reason="Bitbucket does not support a compare api yet. Read more here https://bitbucket.org/site/master/issues/4779/ability-to-diff-between-any-two-commits.")

    @gen.coroutine
    def get_commit_diff(self, commitid, context=None):
        # https://confluence.atlassian.com/bitbucket/diff-resource-425462484.html
        diff = yield self.api('2', 'get', '/repositories/'+self['owner']['username']+'/'+self['repo']['name']+'/diff/'+commitid)
        raise gen.Return(self.diff_to_json(diff))
