class Yaml:

    @staticmethod
    def walk(_dict, keys, _else=None):
        try:
            for key in keys:
                if hasattr(_dict, '_asdict'):
                    # namedtuples
                    _dict = getattr(_dict, key)
                elif hasattr(_dict, '__getitem__'):
                    _dict = _dict[key]
                else:
                    _dict = getattr(_dict, key)
            return _dict
        except:
            return _else
