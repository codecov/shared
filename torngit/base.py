import re
import os
from tornado.httpclient import AsyncHTTPClient


get_start_of_line = re.compile(r"@@ \-(\d+),?(\d*) \+(\d+),?(\d*).*").match


class LoginRequired(Exception):
    pass


class BaseHandler:
    debug = (os.getenv('DEBUG') == 'TRUE' or os.getenv('CI') == 'TRUE')
    _log_handler = None
    _repo_url = None
    _client = None
    _aws_key = None
    _ioloop = None
    _token = None
    timeouts = tuple(map(int, os.getenv('ASYNC_TIMEOUTS', '5,15').split(',')))

    @classmethod
    def new(cls, ioloop=None, log_handler=None, **kwargs):
        self = cls()
        self._ioloop = ioloop
        self._token = kwargs.pop('token', None)
        self.data = {
            "owner": {},
            "repo": {}
        }
        self._log_handler = log_handler
        self.data.update(kwargs)
        return self

    def log(self, **kwargs):
        if self._log_handler:
            self._log_handler(kwargs)

    @property
    def fetch(self):
        if not self._client:
            self._client = AsyncHTTPClient(self._ioloop)
        return self._client.fetch

    def __getitem__(self, index):
        return self.data.get(index)

    def __setitem__(self, index, value):
        self.data[index] = value

    def _validate_language(self, language):
        if language:
            language = language.lower()
            if language in ('javascript', 'shell', 'python', 'ruby', 'perl', 'dart', 'java', 'c', 'clojure', 'd', 'fortran', 'go', 'groovy', 'kotlin', 'php', 'r', 'scala', 'swift', 'objective-c', 'xtend'):
                return language

    def get_href(self, endpoint='repo', **data):
        return ''
        d = self.data.copy()
        d.update(data)
        return (self.service_url + "/" + self.urls[endpoint]) % d

    def get_oauth_token(self, service):
        # overridden in handlers to get current_user details
        return dict(zip(('key', 'secret'), tuple(os.getenv(service.upper() + '_ACCESS_TOKEN').split(':'))))

    def set_token(self, token):
        self._token = token

    @property
    def token(self):
        if not self._token:
            self._token = self.get_oauth_token(self.service)
        return self._token

    def _oauth_consumer_token(self):
        service = self.service.upper()
        return dict(key=os.getenv('%s_CLIENT_ID' % service, ''),
                    secret=os.getenv('%s_CLIENT_SECRET' % service, ''))

    @property
    def slug(self):
        return (self['owner']['username'] + "/" + self['repo']['name']) if self['repo'].get('name') else None

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
                for source in ('diff --git a/' + _diff).splitlines():
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

        return dict(files=results)
