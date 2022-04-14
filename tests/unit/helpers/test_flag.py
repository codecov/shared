from mock import Mock

from shared.helpers.flag import Flag


def test_report():
    paths = ["a", "b"]
    report = Mock(
        filter=Mock(return_value=Mock(__enter__=lambda self: self, __exit__=Mock())),
        yaml={"flags": {"a": {"paths": paths}}},
    )
    with Flag(report, "a").report:
        report.filter.assert_called_with(paths=paths, flags=["a"])


def test_totals_cached():
    assert Flag(None, "_", totals="<totals>").totals == "<totals>"


def test_totals():
    report = Mock(
        filter=Mock(
            return_value=Mock(
                __enter__=lambda self: self, __exit__=Mock(), totals="<totals>"
            )
        ),
        yaml={},
    )
    assert Flag(report, "_").totals == "<totals>"


def test_apply_diff():
    apply_diff = Mock(return_value="<totals>")
    report = Mock(filter=Mock(return_value=Mock(apply_diff=apply_diff)), yaml={})
    assert Flag(report, "_").apply_diff("<diff>") == "<totals>"
    apply_diff.assert_called_with("<diff>", _save=False)


def test_carryforward_info():
    flag_no_cf_info = Flag(None, "Flag")
    assert flag_no_cf_info.carriedforward is False
    assert flag_no_cf_info.carriedforward_from is None

    flag_with_cf_info = Flag(
        None, "Another flag", carriedforward=True, carriedforward_from="12345"
    )
    assert flag_with_cf_info.carriedforward is True
    assert flag_with_cf_info.carriedforward_from == "12345"
