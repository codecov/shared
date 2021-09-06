from itertools import chain

from colour import Color

colors = list(
    chain(
        Color("#e05d44").range_to("#fe7d37", 20),
        Color("#fe7d37").range_to("#dfb317", 20),
        Color("#dfb317").range_to("#a4a61d", 20),
        Color("#a4a61d").range_to("#97CA00", 20),
        Color("#97CA00").range_to("#4c1", 21),
    )
)


def coverage_to_color(range_low, range_high):
    _div = float(range_high) - float(range_low)

    def _color(cov):
        cov = float(cov or 0)
        if int(cov) == 100:
            return Color(colors[-1].hex)

        if cov <= range_low:
            return Color(colors[0].hex)

        elif cov >= range_high:
            return Color(colors[-1].hex)

        offset = ((float(cov - range_low)) / _div) * 100.0
        return Color(colors[int(offset)].hex)

    return _color
