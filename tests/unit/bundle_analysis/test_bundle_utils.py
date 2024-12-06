from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from shared.bundle_analysis.utils import (
    AssetRoute,
    AssetRoutePluginName,
    split_by_delimiter,
)


@pytest.fixture
def sample_filenames():
    """
    A fixture providing sample filenames for testing different plugins.
    """
    return {
        AssetRoutePluginName.REMIX_VITE: "routes/index.tsx",
        AssetRoutePluginName.NEXTJS_WEBPACK: "pages/api/hello.js",
        AssetRoutePluginName.NUXT: "pages/index.vue",
        AssetRoutePluginName.SOLIDSTART: "routes/dashboard.ts",
        AssetRoutePluginName.SVELTEKIT: "src/routes/about/+page.svelte",
    }


def test_bundle_asset_route_asset_route_remix_vite_get_from_filename():
    """
    Test the get_from_filename method for the Remive Vite plugin.
    """
    plugin = AssetRoutePluginName.REMIX_VITE

    # Valid cases
    valid_cases = [
        ("./app/routes/_index.tsx", "/"),  # Root
        (
            "app/routes/_index.tsx?__remix-build-client-route",
            "/",
        ),  # With parameter after extension
        ("app/routes/about.tsx", "/about"),  # Base case
        ("app/routes/concerts.new-york.jsx", "/concerts/new-york"),  # Dot delimiters
        ("app/routes/concerts.$city.ts", "/concerts/$city"),  # Dynamic segments
        ("app/routes/concerts._index.js", "/concerts"),  # Nested routes
        (
            "app/routes/concerts_.mine.tsx",
            "/concerts/mine",
        ),  # Nested URLs without Layout Nesting
        (
            "app/routes/_auth.register.tsx",
            "/register",
        ),  # Nested Layouts without Nested URLs
        (
            "app/routes/($lang).$productId.jsx",
            "/($lang)/$productId",
        ),  # Optional segments
        ("app/routes/files.$.tsx", "/files/$"),  # Splat routes
        # Escaping Special Characters
        ("app/routes/sitemap[.]xml.tsx", "/sitemap.xml"),
        ("app/routes/[sitemap.xml].tsx", "/sitemap.xml"),
        ("app/routes/weird-url.[_index].tsx", "/weird-url"),
        ("app/routes/dolla-bills-[$].tsx", "/dolla-bills-$"),
        ("app/routes/[[so-weird]].tsx", "/[so-weird]"),
    ]

    # Invalid cases
    invalid_cases = [
        ("hello.js", None),  # Contain at lease 3 parts
        ("app/bout/hello.js", None),  # Prefix is present
        ("gap/routest/hello.js", None),  # Prefix is present
        ("app/routes/.hiddenfile", None),  # Hidden file (no valid name)
        ("app/routes/invalidfile.", None),  # Ends with a dot
        ("app/routes/invalidfile", None),  # No dot (not a file)
        ("app/routes/badextension.py", None),  # Not valid extension
    ]

    # Test valid cases
    for filename, expected in valid_cases:
        asset_route = AssetRoute(plugin=plugin)
        result = asset_route.get_from_filename(filename=filename)
        assert result == expected, f"Failed for valid case: {filename}"

    # Test invalid cases
    for filename, expected in invalid_cases:
        asset_route = AssetRoute(plugin=plugin)
        result = asset_route.get_from_filename(filename=filename)
        assert result == expected, f"Failed for invalid case: {filename}"


def test_bundle_asset_route_nextjs_webpack_get_from_filename():
    """
    Test the get_from_filename method for the Next.js Webpack plugin.
    """
    plugin = AssetRoutePluginName.NEXTJS_WEBPACK

    # Valid cases
    valid_cases = [
        ("app/pages/api/hello.js", "/pages/api"),
        ("app/pages/index.jsx", "/pages"),
        ("app/components/page.module.css", "/components"),
        ("app/pages/subdir/index.tsx", "/pages/subdir"),
    ]

    # Invalid cases
    invalid_cases = [
        ("pages/api/hello.js", None),  # Missing `app` prefix
        ("app/pages/api/", None),  # Last part is not a file
        ("app/pages", None),  # Not enough parts
        ("app/pages/.hiddenfile", None),  # Hidden file (no valid name)
        ("app/pages/invalidfile.", None),  # Ends with a dot
        ("app/pages/invalidfile", None),  # No dot (not a file)
    ]

    # Test valid cases
    for filename, expected in valid_cases:
        asset_route = AssetRoute(plugin=plugin)
        result = asset_route.get_from_filename(filename=filename)
        assert result == expected, f"Failed for valid case: {filename}"

    # Test invalid cases
    for filename, expected in invalid_cases:
        asset_route = AssetRoute(plugin=plugin)
        result = asset_route.get_from_filename(filename=filename)
        assert result == expected, f"Failed for invalid case: {filename}"


def test_bundle_asset_route_nuxt_get_from_filename():
    """
    Test the get_from_filename method for the Nuxt plugin.
    """
    plugin = AssetRoutePluginName.NUXT

    # Valid cases
    valid_cases = [
        ("pages/api/hello.vue", "/api/hello"),
        ("pages/index.vue", "/"),
        ("pages/[components]/page.module.vue", "/[components]/page.module"),
        ("pages/pages/subdir/index.vue", "/pages/subdir"),
        ("pages/pages/subdir/[id].vue", "/pages/subdir/[id]"),
    ]

    # Invalid cases
    invalid_cases = [
        ("app/api/hello.vue", None),  # Missing `pages` prefix
        ("pages/pages/api/", None),  # Last part is not a file
        ("pages/pages/.js", None),  # Not vue file (no valid name)
        ("pages/pages/invalidfile.", None),  # Ends with a dot
        ("pages/pages/invalidfile", None),  # No dot (not a file)
    ]

    # Test valid cases
    for filename, expected in valid_cases:
        asset_route = AssetRoute(plugin=plugin)
        result = asset_route.get_from_filename(filename=filename)
        assert result == expected, f"Failed for valid case: {filename}"

    # Test invalid cases
    for filename, expected in invalid_cases:
        asset_route = AssetRoute(plugin=plugin)
        result = asset_route.get_from_filename(filename=filename)
        assert result == expected, f"Failed for invalid case: {filename}"


def test_bundle_asset_route_solidstart_get_from_filename():
    """
    Test the get_from_filename method for the SolidStart plugin.
    """
    plugin = AssetRoutePluginName.SOLIDSTART

    # Valid cases
    valid_cases = [
        ("./src/routes/blog.tsx", "/blog"),
        ("src/routes/contact.jsx", "/contact"),
        ("./src/routes/directions.ts", "/directions"),
        ("./src/routes/blog/article-1.js", "/blog/article-1"),
        ("./src/routes/work/job-1.tsx", "/work/job-1"),
        ("./src/routes/index.tsx", "/"),
        ("./src/routes/socials/index.tsx", "/socials"),
        ("./src/routes/users(details)/[id].tsx/", "/users/[id]"),
        ("./src/routes/users/[id]/[name].tsx", "/users/[id]/[name]"),
        ("./src/routes/[...missing].tsx", "/[...missing]"),
        ("./src/routes/[[id]].tsx", "/[[id]]"),
        ("./src/routes/users/(static)/about-us/index.tsx", "/users/about-us"),
    ]

    # Invalid cases
    invalid_cases = [
        ("./src/pages/api/hello.js", None),  # Missing `src/routes` prefix
        ("./src/routes/api/", None),  # Last part is not a file
        ("./src/routes", None),  # Not enough parts
        ("./src/routes/.hiddenfile", None),  # Hidden file (no valid name)
        ("./src/routes/invalidfile.", None),  # Ends with a dot
        ("./src/routes/invalidfile", None),  # No dot (not a file)
    ]

    # Test valid cases
    for filename, expected in valid_cases:
        asset_route = AssetRoute(plugin=plugin)
        result = asset_route.get_from_filename(filename=filename)
        assert result == expected, f"Failed for valid case: {filename}"

    # Test invalid cases
    for filename, expected in invalid_cases:
        asset_route = AssetRoute(plugin=plugin)
        result = asset_route.get_from_filename(filename=filename)
        assert result == expected, f"Failed for invalid case: {filename}"


def test_bundle_asset_route_sveltekit_get_from_filename():
    """
    Test the get_from_filename method for the SvelteKit plugin.
    """
    plugin = AssetRoutePluginName.SVELTEKIT

    # Valid cases
    valid_cases = [
        ("src/routes/about/+page.svelte", "/about"),
        ("src/routes/blog/post/+page.svelte", "/blog/post"),
        ("src/routes/+layout.svelte", "/"),
        ("src/routes/subdir/+layout.svelte", "/subdir"),
        ("src/routes/deep/nested/+page.svelte", "/deep/nested"),
    ]

    # Invalid cases
    invalid_cases = [
        ("src/routes/notafile.txt", None),  # Missing "+"
        ("src/routes/notafile", None),  # No file extension
        ("src/routes/notafile.", None),  # Ends with a dot
        ("src/routes/+folder/", None),  # Suffix is not a file
        ("src/routes/+foldername", None),  # Missing file extension
        ("src/+folder/+page.svelte", None),  # Prefix missing "routes"
        ("routes/+page.svelte", None),  # Missing "src" in prefix
        ("src/not_routes/+page.svelte", None),  # Prefix mismatch
        ("src/routes/", None),  # Missing file suffix
        ("src/routes/not_a_file.svelte", None),  # Missing "+" prefix in file
    ]

    # Test valid cases
    for filename, expected in valid_cases:
        asset_route = AssetRoute(plugin=plugin)
        result = asset_route.get_from_filename(filename=filename)
        assert result == expected, f"Failed for valid case: {filename}"

    # Test invalid cases
    for filename, expected in invalid_cases:
        asset_route = AssetRoute(plugin=plugin)
        result = asset_route.get_from_filename(filename=filename)
        assert result == expected, f"Failed for invalid case: {filename}"


def test_bundle_asset_route_asset_route_astro_get_from_filename():
    """
    Test the get_from_filename method for the Astro plugin.
    """
    plugin = AssetRoutePluginName.ASTRO

    # Valid cases
    valid_cases = [
        ("./src/pages/index.astro", "/"),  # Root
        (
            "src/pages/index.ts?__client-route",
            "/",
        ),  # With parameter after extension
        ("src/pages/about.md", "/about"),  # Base case
        ("src/pages/concerts/new-york.mdx", "/concerts/new-york"),  # Multiple
        ("src/pages/concerts/index.ts", "/concerts"),  # Dynamic segments
        (
            "src/pages/[concerts].html",
            "/[concerts]",
        ),  # HTML
        (
            "src/pages/[city]/[..concerts]/[band].astro",
            "/[city]/[..concerts]/[band]",
        ),  # Dot dot expansion
        # Ignoring underscore prefix
        ("src/pages/_city/index.ts", None),
        ("src/pages/city/_bank/index.ts", None),
        ("src/pages/city/bank/_index.ts", None),
        ("src/pages/city/bank/_post.ts", None),
    ]

    # Invalid cases
    invalid_cases = [
        ("hello.js", None),  # Contain at lease 3 parts
        ("app/bout/hello.js", None),  # Prefix is not present
        ("gap/routest/hello.js", None),  # Prefix is not present
        ("src/pages/.hiddenfile", None),  # Hidden file (no valid name)
        ("src/pages/invalidfile.", None),  # Ends with a dot
        ("src/pages/invalidfile", None),  # No dot (not a file)
        ("src/pages/badextension.py", None),  # Not valid extension
    ]

    # Test valid cases
    for filename, expected in valid_cases:
        asset_route = AssetRoute(plugin=plugin)
        result = asset_route.get_from_filename(filename=filename)
        assert result == expected, f"Failed for valid case: {filename}"

    # Test invalid cases
    for filename, expected in invalid_cases:
        asset_route = AssetRoute(plugin=plugin)
        result = asset_route.get_from_filename(filename=filename)
        assert result == expected, f"Failed for invalid case: {filename}"


def test_bundle_asset_route_exception_handling():
    """
    Test that get_from_filename correctly handles exceptions and logs them.
    """
    plugin = AssetRoutePluginName.REMIX_VITE
    filename = "invalid_filename"

    # Mock the `_compute_from_filename` method to raise an exception
    with patch("shared.bundle_analysis.utils.log") as mock_log:
        asset_route = AssetRoute(plugin=plugin)
        asset_route._compute_from_filename = MagicMock(
            side_effect=ValueError("Test exception")
        )

        # Call the method and check the return value
        result = asset_route.get_from_filename(filename=filename)

        # Verify that None is returned
        assert result is None

        # Verify that the error was logged
        mock_log.error.assert_called_once()
        assert (
            "Uncaught error during AssetRoute path compute"
            in mock_log.error.call_args[0][0]
        )


@pytest.mark.parametrize(
    "input_str, extensions, expected",
    [
        # Generic file validation (no extension specified)
        ("file.txt", None, True),
        ("page.module.css", None, True),
        ("file", None, False),
        ("dir/file.js", None, False),  # Invalid: contains directory separator
        # Specific extension validation
        ("file.txt", ["txt"], True),
        ("page.module.css", ["css"], True),
        ("file.txt", ["css"], False),
        ("file", ["txt"], False),
        ("dir/file.txt", ["txt"], False),  # Invalid: contains directory separator
        ("file.css.js", ["js"], True),  # Multiple dots, ends with js
        ("file.css.js", ["css"], False),  # Ends with js, not css
        ("file.", ["txt"], False),  # Invalid: no characters after the dot
    ],
)
def test_bundle_asset_route_is_file(input_str, extensions, expected):
    asset_route = AssetRoute(plugin=AssetRoutePluginName.NEXTJS_WEBPACK)
    result = asset_route._is_file(input_str, extensions)
    assert result == expected, f"Failed for input: {input_str}, extension: {extensions}"


@pytest.mark.parametrize(
    "s, splitter, escape_open, escape_close, expected",
    [
        # Basic splitting without escapes
        ("a.b.c", ".", None, None, ["a", "b", "c"]),
        ("a,b,c", ",", None, None, ["a", "b", "c"]),
        ("a;b;c", ";", None, None, ["a", "b", "c"]),
        # Splitting with escapes
        ("a[.]b.c", ".", "[", "]", ["a.b", "c"]),
        ("[a.]b.c", ".", "[", "]", ["a.b", "c"]),
        ("[a.].b.c", ".", "[", "]", ["a.", "b", "c"]),
        ("[a[.]b].c", ".", "[", "]", ["a[.]b", "c"]),
        ("a<b>b<c", ">", "<", ">", []),
        # No splitting for unmatched escapes
        ("[a.b.c", ".", "[", "]", []),
        ("a.b.c]", ".", "[", "]", []),
        # Invalid input handling (invalid splitter, escape_open, or escape_close)
        ("a.b.c", "dot", None, None, []),  # Splitter not 1 char
        ("a.b.c", ".", "[", None, []),  # escape_close is None
        ("a.b.c", ".", None, "]", []),  # escape_open is None
        ("a.b.c", ".", "[[", "]", []),  # escape_open not 1 char
        ("a.b.c", ".", "[", "]]", []),  # escape_close not 1 char
        # Empty string
        ("", ".", None, None, []),
        ("", ".", "[", "]", []),
        # String with no splitters
        ("abc", ".", None, None, ["abc"]),
        ("abc", ",", None, None, ["abc"]),
        # String with only splitters
        ("...", ".", None, None, ["", "", "", ""]),
        (",,,", ",", None, None, ["", "", "", ""]),
        # Edge cases with nested escapes
        ("[a[b.c]].d", ".", "[", "]", ["a[b.c]", "d"]),
        ("[a[b[c.d]]].e", ".", "[", "]", ["a[b[c.d]]", "e"]),
        ("[a.b.c]", ".", "[", "]", ["a.b.c"]),
        ("[a[.]b.c]", ".", "[", "]", ["a[.]b.c"]),
        ("[[a]].b", ".", "[", "]", ["[a]", "b"]),
        # Validation: Splitter identical to escape characters (should return [])
        ("a<b>b<c", "<", "<", ">", []),  # Splitter == escape_open
        ("a<b>b<c", ">", "<", ">", []),  # Splitter == escape_close
        # Validation: Unmatched escapes (should return [])
        ("a<b>b<c", ".", "<", ">", []),  # Unmatched escape
        ("a<b>b>c>", ".", "<", ">", []),  # Extra closing escape
    ],
)
def test_bundle_asset_route_split_by_delimiter(
    s: str,
    splitter: str,
    escape_open: Optional[str],
    escape_close: Optional[str],
    expected: List[str],
):
    assert split_by_delimiter(s, splitter, escape_open, escape_close) == expected
