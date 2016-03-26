import re
import os
from tornwrap import logger
from tornado.httpclient import AsyncHTTPClient


get_start_of_line = re.compile(r"@@ \-(\d+),?(\d*) \+(\d+),?(\d*).*").match


class BaseHandler:
    _log_handler = None
    _repo_url = None
    _client = None
    _aws_key = None
    _ioloop = None
    _oauth = None
    _token = None
    timeouts = tuple(map(int, os.getenv('ASYNC_TIMEOUTS', '5,15').split(',')))

    # Important. Leave this commented out to properly override
    # def get_oauth_token(self, service):
    #     return dict(key=os.getenv(service.upper() + '_ACCESS_TOKEN'),
    #                 secret=os.getenv(service.upper() + '_ACCESS_TOKEN_SECRET'),
    #                 username='_guest_')

    def _oauth_consumer_token(self):
        return self._oauth or self.get_oauth_consumer_token()

    @classmethod
    def new(cls, ioloop=None, log_handler=None, oauth_consumer_token=None, **kwargs):
        self = cls()
        self._ioloop = ioloop
        self._token = kwargs.pop('token', None)
        self._oauth = oauth_consumer_token
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

        default = getattr(self, 'get_log_payload', dict)()
        if hasattr(self, 'request_id'):
            default['id'] = self.request_id
        default.update(kwargs)
        logger.log(**default)

    @property
    def fetch(self):
        if not self._client:
            self._client = AsyncHTTPClient(self._ioloop)
        return self._client.fetch

    def _validate_language(self, language):
        if language:
            language = language.lower()
            if language in ('javascript', 'shell', 'python', 'ruby', 'perl', 'dart', 'java', 'c', 'clojure', 'd', 'fortran', 'go', 'groovy', 'kotlin', 'php', 'r', 'scala', 'swift', 'objective-c', 'xtend'):
                return language

    def renamed_repository(self, repo):
        pass

    def get_href(self, endpoint='repo', **data):
        d = self.data['owner'].copy()
        d.update(self.data['repo'])
        d.update(self.data.get('commit', {}))
        d.update(data)
        d = dict([(k, str(v).encode('utf-8')) for k, v in d.iteritems()])
        # TODO need to test this to make sure the correct escaping happens for emojis
        return (self.service_url + "/" + self.urls[endpoint]) % d

    def set_token(self, token):
        self._token = token

    @property
    def token(self):
        if not self._token:
            self._token = self.get_oauth_token(self.service)
        return self._token

    @property
    def slug(self):
        return (self.data['owner']['username'] + "/" + self.data['repo']['name']) if self.data['repo'].get('name') else None

    def diff_to_json(self, diff):
        """
        Processes a full diff (multiple files) into the object pattern below
        docs/specs/diff.json
        """
        results = {}
        diff = ('\n'+diff).split('\ndiff --git a/')[1:]
        segment = None
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
                    if source == '\ No newline at end of file':
                        break

                    sol4 = source[:4]
                    if sol4 == '--- ' and source != '--- /dev/null':
                        _file['before'] = source[6:] if source[4:6] in ('a/', 'b/') else source[4:]
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

                    # else:
                    #     results.pop(fname)
                    #     break

        return self._add_diff_totals(dict(files=results)) if results else None

    def _add_diff_totals(self, diff):
        for fname, data in diff['files'].iteritems():
            rm = 0
            add = 0
            for segment in data['segments']:
                rm += sum([1 for line in segment['lines'] if line[0] == '-'])
                add += sum([1 for line in segment['lines'] if line[0] == '+'])
            data['totals'] = dict(added=add, removed=rm)
        return diff
