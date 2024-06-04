from enum import Enum

from shared.reports.types import ReportTotals


class SessionType(Enum):
    uploaded = "uploaded"
    carriedforward = "carriedforward"

    @classmethod
    def get_from_string(cls, val):
        for member in cls:
            if member.value == val:
                return member
        return None


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
        session_extras=None,
        **kwargs,
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
        self.session_extras = session_extras or {}

    def __eq__(self, other):
        return (
            self.id == other.id
            and self.totals == other.totals
            and self.time == other.time
            and self.archive == other.archive
            and self.flags == other.flags
            and self.provider == other.provider
            and self.build == other.build
            and self.job == other.job
            and self.url == other.url
            and self.state == other.state
            and self.env == other.env
            and self.name == other.name
            and self.session_type == other.session_type
            and self.session_extras == other.session_extras
        )

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
        se=None,
        **kwargs,
    ):
        return cls(
            id=id,
            totals=parse_totals(t or kwargs.get("totals")),
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
            session_type=SessionType.get_from_string(st),
            session_extras=se,
        )

    def _encode(self):
        return {
            "t": self.totals.astuple()
            if isinstance(self.totals, ReportTotals)
            else self.totals,
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
            "st": self.session_type.value,
            "se": self.session_extras,
        }


def parse_totals(totals):
    if isinstance(totals, ReportTotals):
        return totals
    if totals:
        return ReportTotals(*totals)
    return None
