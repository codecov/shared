import re
import os
from tornado import gen
from tornado.httputil import url_concat
from requests.exceptions import HTTPError
from tornado.httpclient import AsyncHTTPClient


get_start_of_line = re.compile(r"@@ \-(\d+),?(\d*) \+(\d+),?(\d*).*").match


def iterlines(doc):
    prevnl = -1
    while True:
        nextnl = doc.find('\n', prevnl + 1)
        if nextnl < 0:
            break
        yield doc[prevnl + 1:nextnl]
        prevnl = nextnl


class LoginRequired(Exception):
    pass


class BaseHandler:
    debug = (os.getenv('DEBUG') == 'TRUE' or os.getenv('CI') == 'TRUE')
    _aws_key = None
    _repo_url = None
    _client = None
    _ioloop = None

    def log(self, *a, **k):
        print "\033[92m..LOG..\033[0m", a, k

    @property
    def fetch(self):
        if not self._client:
            self._client = AsyncHTTPClient(self._ioloop)
        return self._client.fetch

    def get_oauth_token(self, service):
        return dict(zip(('key', 'secret'), tuple(os.getenv(service.upper() + '_ACCESS_TOKEN').split(':'))))

    def __init__(self, service_id, username, repo, token=None, ioloop=None, **kwargs):
        self._ioloop = ioloop
        self.set_token(token)
        self.data = {}
        self.data.update(kwargs)
        self.data.update(dict(repo_service_id=service_id, username=username, repo=repo))

    def __getitem__(self, index):
        return self.data.get(index)

    def __setitem__(self, index, value):
        self.data[index] = value

    @property
    def uri(self):
        return '/'.join(('', self.service, self['username'], self['repo']))

    def get_repo_url(self, *url, **query):
        if self._repo_url is None:
            self._repo_url = ('/'.join((os.getenv('CODECOV_URL'), self.service, self['username'], self['repo'])), )
        return url_concat('/'.join(self._repo_url + filter(lambda a: a, url)),
                          dict([(k, v) for k, v in query.iteritems() if v]))

    def get_link_to(self, endpoint='repo', **data):
        return ''
        d = self.data.copy()
        d.update(data)
        return (self.service_url + "/" + self.urls[endpoint]) % d

    # def get_oauth_token(self, service):
    #     raise NotImplemented()

    @property
    def token(self):
        if not hasattr(self, '_token'):
            self._token = self.get_oauth_token(self.service)
        return self._token


# class ServiceEngine(ServiceBase):
#     def __init__(self, repo_service_id, username, repo, token=None, **data):
#         data.update(dict(repo_service_id=repo_service_id, username=username, repo=repo))
#         self.set_token(token)
#         self.data = data
#         self.debug = data.get('debug') or (os.getenv("LOGLVL") == "DEBUG")
#         self.data.setdefault('ok', False)

    # def handle_error(self, error):
        # return {}

    # def __getattr__(self, index):
    #     return self.data[index]

    def set_token(self, token=None):
        if token:
            assert set(token.keys()) == set(('key', 'secret', 'username')), 'missing token keys'
            self._token = token
        else:
            self._token = dict(zip(('key', 'secret'), tuple(os.getenv('%s_ACCESS_TOKEN' % self.service.upper()).split(':'))))
            self._token['username'] = ''

    # def get_url(self, *url, **query):
    #     return url_concat("/".join((os.getenv('CODECOV_URL', 'https://codecov.io').strip('/'), ) + (self.service, self.username, self.repo) + url), query)

    @property
    def slug(self):
        return (self['username'] + "/" + self['repo']) if self['repo'] else None

    # def log(self, **kwargs):
    #     kwargs.update(dict(service=self.service, slug=self.slug))
    #     if self.data.get('commit'):
    #         kwargs.setdefault('commit', self.data['commit'][:7])
        # logger.log(**kwargs)

    def diff_to_json(self, diff):
        """
        Processes a full diff (multiple files) into the object pattern below
        docs/specs/diff.json
        """
        results = {}
        diff = ('\n'+diff).split('\ndiff --git a/')[1:]
        for fnum, _diff in enumerate(diff):
            slt = _diff.split('\n', 2) + ['', '']
            fname = slt[0].split(' b/')[-1]
            _file = results[fname] = dict(type=None)

            # Is the file empty, skipped, etc
            # -------------------------------
            if slt[1][:17] == 'deleted file mode':
                _file['type'] = 'deleted'

            else:
                _file['type'] = 'modified'
                _file['before'] = None
                _file['segments'] = []

                # Get coverage data on each line
                # ------------------------------
                # make file, this is ONE file not multiple
                for source in iterlines('diff --git a/' + _diff + '\n'):
                    sol4 = source[:4]
                    if sol4 == '--- ' and source != '--- /dev/null':
                        _file['before'] = source[6:]
                        _file['type'] = 'new'

                    elif sol4 == 'new ':
                        _file['type'] = 'new'

                    elif sol4 == 'Bina':
                        _file['type'] = 'binary'
                        _file.pop('before')
                        _file.pop('segments')
                        break

                    elif sol4 in ('--- ', '+++ ', 'inde', 'diff'):
                        # diff --git a/app/commit.py b/app/commit.py
                        # new file mode 100644
                        # index 0000000..d5ee3d6
                        # --- /dev/null
                        # +++ b/app/commit.py
                        continue

                    elif sol4 == '@@ -':
                        # ex: "@@ -31,8 +31,8 @@ blah blah blah"
                        # ex: "@@ -0,0 +1 @@"
                        l = get_start_of_line(source).groups()
                        segment = dict(header=[l[0], l[1], l[2], l[3]], lines=[])
                        _file['segments'].append(segment)

                    elif source == '':
                        break

                    else:
                        # actual lines
                        segment['lines'].append(source)

        return dict(files=results,
                    totals=dict())
