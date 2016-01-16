import os
import requests
from json import dumps
import urllib as urllib_parse
from collections import defaultdict
from requests_oauthlib import OAuth1

from scms.scm import ServiceBase, ServiceEngine, api


class Bitbucket(ServiceBase):
    service = 'bitbucket'
    service_url = "https://bitbucket.org"
    api_url = "https://bitbucket.org"
    icon = 'fa-bitbucket'

    urls = dict(repo='%(username)s/%(repo)s',
                owner='%(username)s',
                commit='%(username)s/%(repo)s/commits/%(commitid)s',
                commits='%(username)s/%(repo)s/commits',
                blob='%(username)s/%(repo)s/src/%(commitid)s/%(path)s',
                tree='%(username)s/%(repo)s/src/%(commitid)s',
                branch='%(username)s/%(repo)s/branch/%(branch)s',
                pr='%(username)s/%(repo)s/pull-requests/%(pr)s',
                compare='%(username)s/%(repo)s/')


class Bitbucket(ServiceEngine, Bitbucket):
    @property
    def headers(self):
        return dict(timeout=tuple(map(int, os.getenv('ASYNC_TIMEOUTS', '5,15').split(',', 1))),
                    auth=OAuth1(os.getenv('BITBUCKET_CLIENT_ID'), os.getenv('BITBUCKET_CLIENT_SECRET'),
                                self.token['key'], self.token['secret']))

    @api
    def find_pull_request(self, commit, branch):
        # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource#pullrequestsResource-GETalistofopenpullrequests
        results = requests.get(self.api_url + '/api/2.0/repositories/%s/%s/pullrequests?state=OPEN' % (self.username, self.repo), **self.headers)
        if results.status_code == 200:
            for res in results.json()['values']:
                if res['source']['branch']['name'] == branch:
                    return dict(base=dict(branch=res['destination']['branch']['name'],
                                          commit=res['destination']['commit']['hash']),  # its only 12 long...ugh
                                head=dict(branch=res['source']['branch']['name'],
                                          commit=res['source']['commit']['hash']),
                                open=res['state'] == 'OPEN',
                                id=res['id'], number=res['id'])

    @api
    def refresh(self, username, ownerid):
        repositories, page = [], 0
        while True:
            page += 1
            # https://confluence.atlassian.com/display/BITBUCKET/repositories+Endpoint#repositoriesEndpoint-GETalistofrepositoriesforanaccount
            res = requests.get(self.api_url + "/api/2.0/repositories/%s?page=%d" % (username, page), **self.headers)
            data = []
            repos = res.json()
            for repo in repos['values']:
                _o, _r, _p = repo['owner']['username'], repo['full_name'].split('/', 1)[1], repo['is_private']
                data.append(dict(repo_service_id=repo['uuid'][1:-1], owner_service_id=repo['owner']['uuid'][1:-1],
                                 username=_o, repo=_r, private=_p, branch='master', fork=None))
            self.db.execute("SELECT refresh_repos('bitbucket', '%s'::json);" % dumps(data))
            if not repos.get('next'):
                break

    @api
    def get_pull_request(self, pr):
        # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource#pullrequestsResource-GETaspecificpullrequest
        res = requests.get(self.api_url + "/api/2.0/repositories/%s/pullrequests/%s" % (self.slug, pr), **self.headers)
        res.raise_for_status()
        res = res.json()
        return dict(base=dict(branch=res['destination']['branch']['name'],
                              commit=res['destination']['commit']['hash']),  # its only 12 long...ugh
                    head=dict(branch=res['source']['branch']['name'],
                              commit=res['source']['commit']['hash']),
                    open=res['state'] == 'OPEN',
                    id=res['id'], number=pr)

    @api
    def post_comment(self, issueid, body):
        # https://confluence.atlassian.com/display/BITBUCKET/issues+Resource#issuesResource-POSTanewcommentontheissue
        res = requests.post(self.api_url + "/api/1.0/repositories/%s/pullrequests/%s/comments" % (self.slug, str(issueid)),
                            data=urllib_parse.urlencode(dict(content=body)), **self.headers)
        res.raise_for_status()
        commentid = res.json()['comment_id']
        return commentid

    @api
    def edit_comment(self, issueid, commentid, body):
        # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource+1.0#pullrequestsResource1.0-PUTanupdateonacomment
        res = requests.put(self.api_url + "/api/1.0/repositories/%s/pullrequests/%s/comments/%s" % (self.slug, str(issueid), str(commentid)),
                           data=urllib_parse.urlencode(dict(content=body)), **self.headers)
        res.raise_for_status()
        return True

    @api
    def get_commit_status(self, commit, _merge=None):
        # https://confluence.atlassian.com/bitbucket/buildstatus-resource-779295267.html
        # Cannot get "all" builds only lookup by vendor
        return ('builds', None)

    @api
    def post_status(self, commit, status, context, description, url=None, _merge=None):
        # https://confluence.atlassian.com/bitbucket/buildstatus-resource-779295267.html
        status = dict(pending='INPROGRESS', success='SUCCESSFUL', error='FAILED', failure='FAILED').get(status)
        assert status, 'status not valid'
        res = requests.post(self.api_url + "/api/2.0/%s/commit/%s/statuses/build" % (self.slug, commit),
                            data=dumps(dict(state=status,
                                            key='codecov-'+context,
                                            name=context.capitalize()+' Coverage',
                                            url=url or self.get_repo_url(ref=_merge or commit),
                                            description=description)), **self.headers)
        if res.status_code not in (200, 201):
            res = requests.put(self.api_url + "/api/2.0/%s/commit/%s/statuses/build/codecov-%s" % (self.slug, commit, context),
                               data=dumps(dict(state=status,
                                               name=context.capitalize()+' Coverage',
                                               url=url or self.get_repo_url(ref=_merge or commit),
                                               description=description)), **self.headers)

        res.raise_for_status()
        # check if the commit is a Merge
        return res.json()

    @api
    def get_user_id(self, login):
        # https://confluence.atlassian.com/display/BITBUCKET/users+Endpoint#usersEndpoint-GETtheuserprofile
        res = requests.get(self.api_url + '/api/2.0/users/' + login, **self.headers)
        res.raise_for_status()
        return res.json()['uuid'][1:-1]

    @api
    def get_commit(self, commit):
        # https://confluence.atlassian.com/display/BITBUCKET/commits+or+commit+Resource#commitsorcommitResource-GETanindividualcommit
        res = requests.get(self.api_url + "/api/2.0/repositories/%s/commit/%s" % (self.slug, str(commit)), **self.headers)
        res.raise_for_status()
        data = res.json()
        author_login = data['author'].get('user', {}).get('username')
        author_raw = data['author']['raw'][:-1].rsplit(' <', 1)
        return dict(author_id=self.get_user_id(author_login) if author_login else None,
                    author_login=author_login,
                    author_name=author_raw[0],
                    author_email=author_raw[1],
                    message=data['message'],
                    date=data['date'])

    @api
    def get_branches(self):
        # https://confluence.atlassian.com/display/BITBUCKET/repository+Resource+1.0#repositoryResource1.0-GETlistofbranches
        res = requests.get(self.api_url + "/api/1.0/repositories/%s/branches" % (self.slug), **self.headers)
        res.raise_for_status()
        data = res.json()
        return [(k, b['raw_node']) for k, b in data.iteritems()]

    @api
    def get_open_prs(self):
        # https://confluence.atlassian.com/display/BITBUCKET/pullrequests+Resource#pullrequestsResource-GETalistofopenpullrequests
        page = 0
        prs = []
        while True:
            page += 1
            res = requests.get(self.api_url + "/api/2.0/repositories/%s/pullrequests?state=OPEN&page=%d" % (self.slug, page), **self.headers)
            res.raise_for_status()
            _prs = res.json()['values']
            if len(_prs) == 0:
                break
            prs.extend([('#'+str(b['id']), b['source']['commit']['hash']) for b in _prs])
            if len(_prs) < 100:
                break
        return prs
