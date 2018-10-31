import unittest
from ddt import ddt, data

from torngit.status import Status


@ddt
class Test(unittest.TestCase):
    @data(([{
        'url': None,
        'state': 'pending',
        'context': 'other',
        'time': '2015-12-21T16:54:13Z'
    }], 'pending', 'just one pending'),
          ([{
              'url': None,
              'state': 'pending',
              'context': 'other',
              'time': '2015-12-21T16:54:13Z'
          },
            {
                'url': None,
                'state': 'failure',
                'context': 'ci',
                'time': '2015-12-21T16:54:13Z'
            }], 'failure', 'other ci should be skipped'),
          ([{
              'url': None,
              'state': 'pending',
              'context': 'ci',
              'time': '2015-12-21T16:55:13Z'
          },
            {
                'url': None,
                'state': 'failure',
                'context': 'ci',
                'time': '2015-12-21T16:54:13Z'
            }], 'pending', 'newest prevails'))
    def test_str(self, statuses_res_why):
        statuses, res, why = statuses_res_why
        assert str(Status(statuses)) == res, why

    @data(('demo/*', 2), ('demo/a', 3), ('blah', 4))
    def test_sub(self, out_l):
        out, li = out_l
        s = Status([{
            'url': None,
            'state': 'pending',
            'context': 'demo/a',
            'time': '2015-12-21T16:54:13Z'
        },
                    {
                        'url': None,
                        'state': 'pending',
                        'context': 'demo/b',
                        'time': '2015-12-21T16:54:13Z'
                    },
                    {
                        'url': None,
                        'state': 'pending',
                        'context': 'ci',
                        'time': '2015-12-21T16:54:13Z'
                    },
                    {
                        'url': None,
                        'state': 'pending',
                        'context': 'other',
                        'time': '2015-12-21T16:54:13Z'
                    }])
        new = s - out
        assert id(new) != id(s), 'original should not be modified'
        assert len(new) == li
        assert out not in new
