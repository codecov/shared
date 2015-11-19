import os
from tornado.httputil import url_concat
from requests.exceptions import HTTPError


def api(func):
    """
    Handle the difference between
        yield <github>.get_repository
    and
        <github>.get_repository

    if 'callback' is provided in the arguments
    """
    def wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
            # if self.debug:
            #     logger.log(func=func.__name__,
            #                slug=self.slug,
            #                repository=self.data,
            #                result=result)
            return result

        except HTTPError as error:
            extra = self.handle_error(error)
            self.log(func=func.__name__, status=error.response.status_code, obo=self.token.get('username'), **extra)

        except Exception as e:
            # requests.exceptions.ConnectionError
            self.log(func=func.__name__, error=str(e))

    return wrapper


class ServiceBase(object):
    # https://github.com/codecov/enterprise/wiki/Configuration#ci-providers
    CI_PROVIDERS = set(filter(bool, os.getenv('CI_PROVIDERS', '').split(',')))
    CI_CONTEXTS = set(('ci', 'semaphoreci', 'pull request validator (cloudbees)', 'continuous-integration', 'buildkite'))
    debug = (os.getenv('DEBUG') == 'TRUE' or os.getenv('CI') == 'TRUE')
    _aws_key = None
    _repo_url = None

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

    def get_service_url(self, endpoint='repo', **data):
        d = self.data.copy()
        d.update(data)
        return (self.service_url + "/" + self.urls[endpoint]) % d


class ServiceEngine(ServiceBase):
    def __init__(self, repo_service_id, username, repo, token=None, **data):
        data.update(dict(repo_service_id=repo_service_id, username=username, repo=repo))
        self.set_token(token)
        self.data = data
        self.debug = data.get('debug') or (os.getenv("LOGLVL") == "DEBUG")
        self.data.setdefault('ok', False)

    def handle_error(self, error):
        return {}

    def __getattr__(self, index):
        return self.data[index]

    def set_token(self, token=None):
        if token and token.get('key'):
            self.token = token
        else:
            self.token = dict(zip(('key', 'secret'), tuple(os.getenv('%s_ACCESS_TOKEN' % self.service.upper()).split(':'))))
            self.token['username'] = 'codecov'

    def get_url(self, *url, **query):
        return url_concat("/".join((os.getenv('CODECOV_URL', 'https://codecov.io').strip('/'), ) + (self.service, self.username, self.repo) + url), query)

    @property
    def slug(self):
        return (self.username + "/" + self.repo) if self.repo else None

    def log(self, **kwargs):
        kwargs.update(dict(service=self.service, slug=self.slug))
        if self.data.get('commit'):
            kwargs.setdefault('commit', self.data['commit'][:7])
        # logger.log(**kwargs)
