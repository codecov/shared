import collections

from shared.helpers.color import coverage_to_color


class Dict(dict):
    def __getitem__(self, index):
        if index in ("__l", "__h"):
            return super(Dict, self).__getitem__(index)
        found = self.get(index)
        if not found:
            found = self[index] = Dict(__l=0, __h=0)
        return found

    def add_child(self, args, value):
        i = self
        i["__l"] += value[0]
        i["__h"] += value[1]
        for arg in args[:-1]:
            i = i[arg]
            i["__l"] += value[0]
            i["__h"] += value[1]
        i[args[-1]] = value


def _dict_to_children(n, d, color, classes):
    if type(d) is tuple:
        c = color(d[2])
        return dict(
            name=n,
            _class=classes.get(n),
            lines=d[0],
            coverage=d[2],
            color=getattr(c, "hex", c),
        )
    try:
        coverage = float(d["__h"]) / float(d["__l"]) * 100.0
    except ZeroDivisionError:
        coverage = 100

    c = color(coverage)

    children = [
        _dict_to_children(key, value, color, classes)
        for key, value in d.items()
        if key not in ("__l", "__h")
    ]

    if len(children) == 1 and children[0].get("children"):
        # only one level, join it
        children[0]["name"] = "%s/%s" % (n, children[0]["name"])
        return children[0]

    return dict(
        coverage=coverage,
        lines=d["__l"],
        color=getattr(c, "hex", c),
        _class=classes.get(n),
        name=n,
        children=children,
    )


def report_to_flare(files, color, classes=None):
    flare = Dict(__l=0, __h=0)
    fa = flare.add_child
    for name, totals in files:
        # fa(('path', 'to', 'file'), (lines, hits, coverage))
        fa(name.split("/"), (totals.lines, totals.hits, totals.coverage))

    return [
        _dict_to_children(
            "",
            flare,
            color
            if isinstance(color, collections.abc.Callable)
            else coverage_to_color(*color)
            if color
            else None,
            classes or {},
        )
    ]
