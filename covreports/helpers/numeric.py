class MaxInt:
    def __init__(self, string):
        pass
        self._value = int(string)
        if len(string) > 5:
            self._value = 99999

    def get_value(self):
        return self._value


def ratio(x, y):
    if x == y:
        return '100'

    elif x == 0 or y == 0:
        return '0'

    return '%.5f' % round((float(x) / float(y)) * 100, 5)

