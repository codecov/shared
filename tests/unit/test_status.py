import pytest

from shared.torngit.status import Status


@pytest.mark.parametrize(
    "statuses, res, why",
    [
        (
            [
                {
                    "url": None,
                    "state": "pending",
                    "context": "other",
                    "time": "2015-12-21T16:54:13Z",
                }
            ],
            "pending",
            "just one pending",
        ),
        (
            [
                {
                    "url": None,
                    "state": "pending",
                    "context": "other",
                    "time": "2015-12-21T16:54:13Z",
                },
                {
                    "url": None,
                    "state": "failure",
                    "context": "ci",
                    "time": "2015-12-21T16:54:13Z",
                },
            ],
            "failure",
            "other ci should be skipped",
        ),
        (
            [
                {
                    "url": None,
                    "state": "pending",
                    "context": "ci",
                    "time": "2015-12-21T16:55:13Z",
                },
                {
                    "url": None,
                    "state": "failure",
                    "context": "ci",
                    "time": "2015-12-21T16:54:13Z",
                },
            ],
            "pending",
            "newest prevails",
        ),
    ],
)
def test_str(statuses, res, why):
    assert str(Status(statuses)) == res, why


@pytest.mark.parametrize("out, li", [("demo/*", 2), ("demo/a", 3), ("blah", 4)])
def test_sub(out, li):
    s = Status(
        [
            {
                "url": None,
                "state": "pending",
                "context": "demo/a",
                "time": "2015-12-21T16:54:13Z",
            },
            {
                "url": None,
                "state": "pending",
                "context": "demo/b",
                "time": "2015-12-21T16:54:13Z",
            },
            {
                "url": None,
                "state": "pending",
                "context": "ci",
                "time": "2015-12-21T16:54:13Z",
            },
            {
                "url": None,
                "state": "pending",
                "context": "other",
                "time": "2015-12-21T16:54:13Z",
            },
        ]
    )
    new = s - out
    assert id(new) != id(s), "original should not be modified"
    assert len(new) == li
    assert out not in new


def test_status_with_none_time():
    s = Status(
        [
            {
                "url": None,
                "state": "pending",
                "context": "demo/a",
                "time": "2015-12-21T16:54:13Z",
            },
            {"url": None, "state": "pending", "context": "demo/b", "time": None},
            {
                "url": None,
                "state": "pending",
                "context": "demo/b",
                "time": "2015-12-21T16:54:13Z",
            },
            {
                "url": None,
                "state": "pending",
                "context": "ci",
                "time": "2015-12-21T16:54:13Z",
            },
            {
                "url": None,
                "state": "pending",
                "context": "other",
                "time": "2015-12-21T16:54:13Z",
            },
        ]
    )
    assert len(s) == 4
    new = s - "demo/*"
    assert len(new) == 2


def test_fetch_most_relevant_status_per_context():
    statuses = [
        {
            "url": None,
            "state": "pending",
            "context": "demo/a",
            "time": "2015-12-21T16:54:13Z",
        },
        {
            "url": None,
            "state": "success",
            "context": "demo/a",
            "time": "2015-12-21T16:54:13Z",
        },
        {"url": None, "state": "pending", "context": "demo/b", "time": None},
        {
            "url": None,
            "state": "pending",
            "context": "demo/b",
            "time": "2015-12-21T16:54:13Z",
        },
        {
            "url": None,
            "state": "pending",
            "context": "ci",
            "time": "2015-12-21T16:54:13Z",
        },
        {
            "url": None,
            "state": "success",
            "context": "ci",
            "time": "2010-12-21T16:54:13Z",
        },
        {"url": None, "state": "pending", "context": "other", "time": None},
    ]
    res = Status._fetch_most_relevant_status_per_context(statuses)
    expected_res = [
        {
            "context": "demo/a",
            "state": "success",
            "time": "2015-12-21T16:54:13Z",
            "url": None,
        },
        {
            "context": "demo/b",
            "state": "pending",
            "time": "2015-12-21T16:54:13Z",
            "url": None,
        },
        {
            "context": "ci",
            "state": "pending",
            "time": "2015-12-21T16:54:13Z",
            "url": None,
        },
        {"context": "other", "state": "pending", "time": None, "url": None},
    ]
    assert expected_res == res
