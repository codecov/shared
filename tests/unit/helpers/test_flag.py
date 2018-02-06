from mock import Mock
from src.helpers.flag import Flag


def test_report():
    """getting report will apply filters"""
    paths = ['a', 'b']
    report = Mock(filter=Mock(return_value=Mock(__enter__=lambda self: self,
                    __exit__=Mock())), yaml={'flags': {'a': {'paths': paths}}})
    with Flag(report, 'a').report:
        report.filter.assert_called_with(paths=paths, flags=['a'])


def test_totals_cached():
    """"caching totals does not filter"""
    assert Flag(None, '_', totals='<totals>').totals == '<totals>'


def test_totals():
    """getting totals will filter and return totals"""
    report = Mock(filter=Mock(return_value=Mock(__enter__=lambda self: self,
                    __exit__=Mock(), totals='<totals>')), yaml={})
    assert Flag(report, '_').totals == '<totals>'


def test_apply_diff():
    """call and returns apply diff"""
    apply_diff = Mock(return_value='<totals>')
    report = Mock(filter=Mock(return_value=Mock(__enter__=lambda self: self,
                    __exit__=Mock(), apply_diff=apply_diff)), yaml={})
    assert Flag(report, '_').apply_diff('<diff>') == '<totals>'
    apply_diff.assert_called_with('<diff>', _save=False)
