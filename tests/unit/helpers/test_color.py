from src.helpers.color import coverage_to_color


def test_color():
    assert coverage_to_color(70, 100)(60.0).hex == '#e05d44'
    assert coverage_to_color(70, 100)(70.0).hex == '#e05d44'
    assert coverage_to_color(70, 100)(80.0).hex == '#efa41b'
    assert coverage_to_color(70, 100)(90.0).hex == '#a3b114'
    assert coverage_to_color(70, 100)(100.0).hex == '#4c1'
    assert coverage_to_color(70, 100)(99.99999).hex == '#48cc10'
    assert coverage_to_color(50, 90)(95.0).hex == '#4c1'
