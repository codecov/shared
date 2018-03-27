class Session(object):
    def __init__(self, id=None, t=None, d=None, a=None, f=None,
                 c=None, n=None, j=None, u=None, p=None, e=None,
                 N=None,
                 **kwargs):
        # the kwargs are for old reports
        self.id = id
        self.totals = t or kwargs.get('totals')
        self.time = d or kwargs.get('time')
        self.archive = a or kwargs.get('archive')  # url where archived
        self.flags = f or kwargs.get('flags')
        self.provider = c or kwargs.get('provider')
        self.build = n or kwargs.get('build')
        self.job = j or kwargs.get('job')
        self.url = u or kwargs.get('url')
        self.state = p or kwargs.get('state')
        self.env = e or kwargs.get('env')
        self.name = N or kwargs.get('name')

    def _encode(self):
        return {
            't': self.totals,
            'd': self.time,
            'a': self.archive,
            'f': self.flags,
            'c': self.provider,
            'n': self.build,
            'N': self.name,
            'j': self.job,
            'u': self.url,
            'p': self.state,
            'e': self.env
        }
