def noop_trace(func):
    return func


class NoOpSpan:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        pass

    def __exit__(*args):
        pass


try:
    """
    If the library using us depends on Sentry, import it and export its trace
    decorator.
    """
    import sentry_sdk

    trace = sentry_sdk.trace
    start_span = sentry_sdk.start_span
except ModuleNotFoundError:
    """
    If the library using us doesn't depend on Sentry, just no-op the trace
    decorator.
    """
    trace = noop_trace
    start_span = NoOpSpan
