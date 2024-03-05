from concurrent.futures import ThreadPoolExecutor

_executor = None


def get_executor():
    global _executor
    if _executor == None:
        print("mattmatt initializing threadpool executor")
        _executor = ThreadPoolExecutor(max_workers=1)
    print("mattmatt returning executor")
    return _executor


def run_in_executor(fn):
    def wrapper(*args, **kwargs):
        print("mattmatt calling wrapper")
        return get_executor().submit(fn, *args, **kwargs).result()

    return wrapper
