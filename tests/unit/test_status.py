import unittest
from ddt import ddt, data

from shared.torngit.status import Status


@ddt
class Test(unittest.TestCase):
    @data(
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
    )
    def test_str(self, statuses_res_why):
        statuses, res, why = statuses_res_why
        assert str(Status(statuses)) == res, why

    @data(("demo/*", 2), ("demo/a", 3), ("blah", 4))
    def test_sub(self, out_l):
        out, li = out_l
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

    def test_status_with_none_time(self):
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
                    "time": None,
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
        assert len(s) == 4
        new = s - "demo/*"
        assert len(new) == 2

    def test_fetch_most_relevant_status_per_context(self):
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
            {
                "url": None,
                "state": "pending",
                "context": "demo/b",
                "time": None,
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
                "state": "success",
                "context": "ci",
                "time": "2010-12-21T16:54:13Z",
            },
            {
                "url": None,
                "state": "pending",
                "context": "other",
                "time": None,
            },
        ]
        res = Status._fetch_most_relevant_status_per_context(statuses)
        expected_res = [
            {'context': 'demo/a', 'state': 'success', 'time': '2015-12-21T16:54:13Z', 'url': None},
            {'context': 'demo/b', 'state': 'pending', 'time': '2015-12-21T16:54:13Z', 'url': None},
            {'context': 'ci', 'state': 'pending', 'time': '2015-12-21T16:54:13Z', 'url': None},
            {'context': 'other', 'state': 'pending', 'time': None, 'url': None}
        ]
        assert expected_res == res
