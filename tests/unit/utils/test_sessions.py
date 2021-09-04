import pytest

from shared.utils.sessions import ReportTotals, Session, SessionType


@pytest.mark.unit
def test_sessions():
    s = Session(
        "id",
        "totals",
        "time",
        "archive",
        "flags",
        "provider",
        "build",
        "job",
        "url",
        "state",
        "env",
        "name",
    )
    assert s._encode() == {
        "t": "totals",
        "d": "time",
        "a": "archive",
        "f": "flags",
        "c": "provider",
        "n": "build",
        "N": "name",
        "j": "job",
        "u": "url",
        "p": "state",
        "e": "env",
        "st": "uploaded",
        "se": {},
    }


def test_parse_session():
    encoded_session = {
        "t": [1, 3, 5, 6],
        "d": "time",
        "a": "archive",
        "f": "flags",
        "c": "provider",
        "n": "build",
        "N": "name",
        "j": "job",
        "u": "url",
        "p": "state",
        "e": "env",
        "st": "uploaded",
        "se": {},
    }
    sess = Session.parse_session(**encoded_session)
    assert sess.totals == ReportTotals(files=1, lines=3, hits=5, misses=6)
    assert sess.time == "time"
    assert sess.archive == "archive"
    assert sess.flags == "flags"
    assert sess.provider == "provider"
    assert sess.build == "build"
    assert sess.job == "job"
    assert sess.url == "url"
    assert sess.state == "state"
    assert sess.env == "env"
    assert sess.name == "name"
    assert sess.session_type == SessionType.uploaded
    assert sess.session_extras == {}


def test_parse_session_parsed_report_totals():
    encoded_session = {
        "t": ReportTotals(files=1, lines=3, hits=5, misses=6),
        "d": "time",
        "a": "archive",
        "f": "flags",
        "c": "provider",
        "n": "build",
        "N": "name",
        "j": "job",
        "u": "url",
        "p": "state",
        "e": "env",
        "st": "uploaded",
        "se": {},
    }
    sess = Session.parse_session(**encoded_session)
    assert sess.totals == ReportTotals(files=1, lines=3, hits=5, misses=6)
    assert sess.time == "time"
    assert sess.archive == "archive"
    assert sess.flags == "flags"
    assert sess.provider == "provider"
    assert sess.build == "build"
    assert sess.job == "job"
    assert sess.url == "url"
    assert sess.state == "state"
    assert sess.env == "env"
    assert sess.name == "name"
    assert sess.session_type == SessionType.uploaded
    assert sess.session_extras == {}


def test_parse_session_then_encode():
    encoded_session = {
        "t": [1, 3, 5, 6],
        "d": "time",
        "a": "archive",
        "f": "flags",
        "c": "provider",
        "n": "build",
        "N": "name",
        "j": "job",
        "u": "url",
        "p": "state",
        "e": "env",
        "st": "uploaded",
        "se": {},
    }
    reencoded_session = {
        "t": (1, 3, 5, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        "d": "time",
        "a": "archive",
        "f": "flags",
        "c": "provider",
        "n": "build",
        "N": "name",
        "j": "job",
        "u": "url",
        "p": "state",
        "e": "env",
        "st": "uploaded",
        "se": {},
    }
    sess = Session.parse_session(**encoded_session)
    assert sess._encode() == reencoded_session
