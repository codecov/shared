from enum import Enum


class SessionType(Enum):
    uploaded = 'uploaded'
    carryforwarded = 'carryforwarded'


class Session(object):
    def __init__(
        self,
        id=None,
        totals=None,
        time=None,
        archive=None,
        flags=None,
        provider=None,
        build=None,
        job=None,
        url=None,
        state=None,
        env=None,
        name=None,
        session_type=None,
        **kwargs
    ):
        # the kwargs are for old reports
        self.id = id
        self.totals = totals
        self.time = time
        self.archive = archive  # url where archived
        self.flags = flags
        self.provider = provider
        self.build = build
        self.job = job
        self.url = url
        self.state = state
        self.env = env
        self.name = name
        self.session_type = session_type or SessionType.uploaded

    def __repr__(self):
        return f"Session<{self._encode()}>"

    @classmethod
    def parse_session(
        cls,
        id=None,
        t=None,
        d=None,
        a=None,
        f=None,
        c=None,
        n=None,
        j=None,
        u=None,
        p=None,
        e=None,
        N=None,
        st=None,
        **kwargs
    ):
        return cls(
            id=id,
            totals=t or kwargs.get("totals"),
            time=d or kwargs.get("time"),
            archive=a or kwargs.get("archive"),
            flags=f or kwargs.get("flags"),
            provider=c or kwargs.get("provider"),
            build=n or kwargs.get("build"),
            job=j or kwargs.get("job"),
            url=u or kwargs.get("url"),
            state=p or kwargs.get("state"),
            env=e or kwargs.get("env"),
            name=N or kwargs.get("name"),
            session_type=st
        )

    def _encode(self):
        return {
            "t": self.totals,
            "d": self.time,
            "a": self.archive,
            "f": self.flags,
            "c": self.provider,
            "n": self.build,
            "N": self.name,
            "j": self.job,
            "u": self.url,
            "p": self.state,
            "e": self.env,
            "st": self.session_type.value
        }
