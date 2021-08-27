def maxint(string):
    if len(string) > 5:
        return 99999
    return int(string)


def ratio(x, y):
    if x == y:
        return "100"

    elif x == 0 or y == 0:
        return "0"

    return "%.5f" % round((float(x) / float(y)) * 100, 5)
