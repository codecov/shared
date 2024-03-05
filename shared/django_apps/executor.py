from concurrent.futures import ThreadPoolExecutor

_executor = None


def get_executor():
    global _executor
    if _executor == None:
        _executor = ThreadPoolExecutor(max_workers=1)
    return _executor


def run_in_executor(fn):
    def wrapper(*args, **kwargs):
        return get_executor().submit(fn, *args, **kwargs).result()

    return wrapper
