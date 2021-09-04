from typing import Dict, List, Tuple, Union
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse

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
    if isinstance(string, str):
        if escape:
            return url_escape(string).replace("%2F", "/")
        return string.encode("utf-8", "replace")
    elif escape:
        return str(string)
    else:
        return string


def make_url(repository, *args, **kwargs):
    args = list(map(lambda a: escape(a, True), list(args)))
    kwargs = dict([(k, escape(v)) for k, v in kwargs.items() if v is not None])
    if repository:
        return url_concat(
            "/".join(
                [
                    get_config("setup", "codecov_url"),
                    services_short[repository.service],
                    repository.slug,
                ]
                + args
            ),
            kwargs,
        )
    else:
        return url_concat("/".join([get_config("setup", "codecov_url")] + args), kwargs)


def url_escape(value):
    """Returns a valid URL-encoded version of the given value."""
    return quote_plus(utf8(value))


def url_concat(
    url: str,
    args: Union[
        None, Dict[str, str], List[Tuple[str, str]], Tuple[Tuple[str, str], ...]
    ],
) -> str:
    """Taken from Tornado.httputil
    https://github.com/tornadoweb/tornado/blob/f059b41d18909f83610bb48eba4678f7f892f52f/tornado/httputil.py#L609

    Concatenate url and arguments regardless of whether
    url has existing query parameters.

    ``args`` may be either a dictionary or a list of key-value pairs
    (the latter allows for multiple values with the same key.

    >>> url_concat("http://example.com/foo", dict(c="d"))
    'http://example.com/foo?c=d'
    >>> url_concat("http://example.com/foo?a=b", dict(c="d"))
    'http://example.com/foo?a=b&c=d'
    >>> url_concat("http://example.com/foo?a=b", [("c", "d"), ("c", "d2")])
    'http://example.com/foo?a=b&c=d&c=d2'
    """
    if args is None:
        return url
    parsed_url = urlparse(url)
    if isinstance(args, dict):
        parsed_query = parse_qsl(parsed_url.query, keep_blank_values=True)
        parsed_query.extend(args.items())
    elif isinstance(args, list) or isinstance(args, tuple):
        parsed_query = parse_qsl(parsed_url.query, keep_blank_values=True)
        parsed_query.extend(args)
    else:
        err = "'args' parameter should be dict, list or tuple. Not {0}".format(
            type(args)
        )
        raise TypeError(err)
    final_query = urlencode(parsed_query)
    url = urlunparse(
        (
            parsed_url[0],
            parsed_url[1],
            parsed_url[2],
            parsed_url[3],
            final_query,
            parsed_url[5],
        )
    )
    return url


_UTF8_TYPES = (bytes, type(None))


def utf8(value):
    """Taken from Tornado.escape
    https://github.com/tornadoweb/tornado/blob/1db5b45918da8303d2c6958ee03dbbd5dc2709e9/tornado/escape.py#L188
    Converts a string argument to a byte string.

    If the argument is already a byte string or None, it is returned unchanged.
    Otherwise it must be a unicode string and is encoded as utf8.
    """
    if isinstance(value, _UTF8_TYPES):
        return value
    assert isinstance(value, str)
    return value.encode("utf-8")
