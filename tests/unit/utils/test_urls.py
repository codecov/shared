# -*- coding: latin-1 -*-

import pytest
from tests.base import BaseTestCase
from covreports.utils.urls import escape, make_url

class TestUrlsUtil(BaseTestCase):

    @pytest.mark.parametrize('string, result', [
        (('ab'+u'\xf1'+'cd', False), b'ab\xc3\xb1cd'),
        (('ab'+u'\xf1'+'cd', True), 'ab%C3%B1cd'),
        ((u'ə/fix-coverage', False), b'\xc3\x89\xc2\x99/fix-coverage'),
        ((u'ə/fix-coverage', True), '%C3%89%C2%99/fix-coverage'),
        ((1, False), 1),
        ((None, False), None),
        ((False, False), False),
        ((True, False), True)
    ])
    def test_escape(self, string, result):
        assert escape(*string) == result

    def test_make_url_escapes_in_path(self, mock_configuration):
        res = make_url(None, u'\xa3')
        assert u'\xa3' not in res
        assert '%C2%A3' in res

    def test_make_url_escapes_in_query(self, mock_configuration):
        res = make_url(None, param=u'\xa3')
        assert u'\xa3' not in res
        assert '%C2%A3' in res

    def test_make_url(self, magic, mock_configuration):
        repo = magic(service='github',
                     slug='owner/repo',)
        assert make_url(repo, 'path', 'to', 'somewhere') == 'https://codecov.io/gh/owner/repo/path/to/somewhere'
        assert make_url(None, 'path', 'to', 'other') == 'https://codecov.io/path/to/other'
        mock_configuration.set_params({
            'setup': {
                'codecov_url': 'https://other.com'
            }
        })
        assert make_url(None, 'path', 'to', 'here') == 'https://other.com/path/to/here'
