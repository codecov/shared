import re
from tornwrap import logger
from tornado.escape import url_escape
from tornado.httpclient import AsyncHTTPClient


get_start_of_line = re.compile(r"@@ \-(\d+),?(\d*) \+(\d+),?(\d*).*").match


def unicode_escape(string, escape=True):
    if isinstance(string, basestring):
        if escape:
            return url_escape(string, plus=False).replace('%2F', '/')
        elif isinstance(string, unicode):
            return string.encode('utf-8')
        return string
    else:
        return str(string)


class BaseHandler:
    _log_handler = None
    _repo_url = None
    _client = None
    _aws_key = None
    _ioloop = None
    _oauth = None
    _token = None

    # Important. Leave this commented out to properly override
    # def get_oauth_token(self, service):

    def _oauth_consumer_token(self):
        return self._oauth or self.get_oauth_consumer_token()

    @classmethod
    def new(cls,
            ioloop=None,
            log_handler=None,
            oauth_consumer_token=None,
            timeouts=None,
            token=None,
            torngit_disable_write=None,
            **kwargs):
        self = cls()
        self._ioloop = ioloop
        self._timeouts = timeouts or [10, 30]
        self._token = token
        self._oauth = oauth_consumer_token
        self.data = {
            'owner': {},
            'repo': {}
        }

        if torngit_disable_write:
            self.torngit_disable_write, self.torngit_disable_write_callback = torngit_disable_write
        else:
            self.torngit_disable_write = False

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

    def __repr__(self):
        return '<%s slug=%s/%s ownerid=%s repoid=%s>' % (self.service, self.slug, self.data['owner'].get('ownerid'), self.data['repo'].get('repoid'))

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

    def get_href(self, endpoint='repo', escape=True, **data):
        if escape:
            data = dict([(k, unicode_escape(v)) for k, v in data.iteritems()])

        data.setdefault('username', self.data['owner']['username'])
        if self.data['repo']:
            data.setdefault('name', self.data['repo']['name'])

        return '%s/%s' % (self.service_url, self.urls[endpoint] % data)

    def set_token(self, token):
        self._token = token

    @property
    def token(self):
        if not self._token:
            self._token = self.get_oauth_token(self.service)
        return self._token

    @property
    def slug(self):
        if self.data['owner'] and self.data['repo']:
            if self.data['owner'].get('username') and self.data['repo'].get('name'):
                return ('%s/%s' % (self.data['owner']['username'], self.data['repo']['name']))

    def diff_to_json(self, diff):
        """
        Processes a full diff (multiple files) into the object pattern below
        docs/specs/diff.json
        """
        results = {}
        diff = ('\n%s' % diff).split('\ndiff --git a/')
        segment = None
        for _diff in diff[1:]:
            _diff = _diff.splitlines()

            before, after = _diff.pop(0).split(' b/', 1)

            # Is the file empty, skipped, etc
            # -------------------------------
            _file = dict(type='new' if before == '/dev/null' else 'modified',
                         before=None if before == after or before == '/dev/null' else before,
                         segments=[])

            results[after] = _file

            # Get coverage data on each line
            # ------------------------------
            # make file, this is ONE file not multiple
            for source in _diff:
                if source == '\ No newline at end of file':
                    break

                sol4 = source[:4]
                if sol4 == 'dele':
                    # deleted file mode 100644
                    _file['before'] = after
                    _file['type'] = 'deleted'
                    _file.pop('segments')
                    break

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
                    continue

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
            if 'segments' in data:
                for segment in data['segments']:
                    rm += sum([1 for line in segment['lines'] if line[0] == '-'])
                    add += sum([1 for line in segment['lines'] if line[0] == '+'])
            data['totals'] = dict(added=add, removed=rm)
        return diff
