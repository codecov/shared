try:
    """
    If the library using us depends on Sentry, import it and export its trace
    decorator.
    """
    import sentry_sdk

    trace = sentry_sdk.trace
except ModuleNotFoundError:
    """
    If the library using us doesn't depend on Sentry, just no-op the trace
    decorator.
    """
    trace = lambda f: f
