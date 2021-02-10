from urllib.parse import urlencode, urlparse, urlunparse, quote_plus
from shared.config import get_config

services_short = dict(
    github="gh",
    github_enterprise="ghe",
    bitbucket="bb",
    bitbucket_server="bbs",
    gitlab="gl",
    gitlab_enterprise="gle",
)


def escape(string, escape=False):
    """Returns a valid URL-encoded version of the given value."""
    if isinstance(string, str):
        string = string.encode("utf-8", "replace")
        if escape:
            string = quote_plus(string).replace("%2F", "/")
        return string
    elif escape:
        return str(string)
    else:
        return string


def make_url(repository, *args, **kwargs):
    args = [escape(arg, True) for arg in args]
    kwargs = {k: escape(v) for k, v in kwargs.items() if v is not None}

    # Codecov URL combines protocol and host, so we split.
    parsed_service = urlparse(get_config("setup", "codecov_url"))
    if repository:
        args = [services_short[repository.service], repository.slug] + args
    path = "/".join(args)
    return urlunparse(
        (
            parsed_service.scheme,
            parsed_service.netloc,
            path,
            "",
            urlencode(kwargs),
            "",
        )
    )
