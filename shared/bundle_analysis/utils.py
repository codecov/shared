import logging
import os
import re
from enum import Enum
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)


class AssetRoutePluginName(Enum):
    REMIX_VITE = "@codecov/remix-vite-plugin"
    NEXTJS_WEBPACK = "@codecov/nextjs-webpack-plugin"
    NUXT = "@codecov/nuxt-plugin"
    SOLIDSTART = "@codecov/solidstart-plugin"
    SVELTEKIT = "@codecov/sveltekit-plugin"


class AssetRoute:
    def __init__(
        self,
        plugin: AssetRoutePluginName,
        configured_route_prefix: Optional[str] = None,
    ) -> None:
        self._from_filename_map = {
            AssetRoutePluginName.REMIX_VITE: (self._compute_remix, ["app", "routes"]),
            AssetRoutePluginName.NEXTJS_WEBPACK: (self._compute_nextjs_webpack, "app"),
            AssetRoutePluginName.NUXT: (self._compute_nuxt, "pages"),
            AssetRoutePluginName.SOLIDSTART: (
                self._compute_solidstart,
                ["src", "routes"],
            ),
            AssetRoutePluginName.SVELTEKIT: (
                self._compute_sveltekit,
                ["src", "routes"],
            ),
        }
        self._compute_from_filename = self._from_filename_map[plugin][0]

        if configured_route_prefix is not None:
            self._prefix = configured_route_prefix
        else:
            self._prefix = self._from_filename_map[plugin][1]

    def _is_file(self, s: str, extensions: Optional[List[str]] = None) -> bool:
        """
        Determines if the passed string represents a file with one or more dots,
        and optionally verifies if it ends with a specific extension.

        Args:
            s (str): The string to check.
            extension (Optional[str]): The file extension to validate (e.g., "vue").

        Returns:
            bool: True if the string represents a valid file, False otherwise.
        """
        # If a list of extensions is provided, check if the string ends with it
        if extensions is not None and not any(
            [s.endswith(f".{e}") for e in extensions]
        ):
            return False

        # Matches strings with at least one non-dot character before the first dot
        # and at least one non-dot character after the last dot.
        file_regex = re.compile(r"^[^/\\]+?\.[^/\\]+$")
        return bool(file_regex.match(s))

    def _compute_remix(self, filename: str) -> Optional[str]:
        """
        Computes the route for Next.js Webpack plugin.
        Doc: https://remix.run/docs/en/main/file-conventions/routes
        """
        path_items = Path(filename).parts

        # Check if contains at least 3 parts (2 prefix and suffix)
        if len(path_items) < 3:
            return None

        # Check if 2 prefix is present
        if path_items[0] != self._prefix[0] or path_items[1] != self._prefix[1]:
            return None

        # Remove parameters after extension
        file = path_items[-1]
        if file.rfind("?") >= 0:
            file = file[: file.rfind("?")]

        # Check if suffix is a file that with valid extensions
        if not self._is_file(file, extensions=["tsx", "ts", "jsx", "js"]):
            return None

        # Get the file name without extension
        file = path_items[-1]
        file = file[: file.rfind(".")]

        returned_path = list(path_items[2:-1])

        # Split the file by . to build the route with special rules
        file_items = split_by_delimiter(
            file, delimiter=".", escape_open="[", escape_close="]"
        )
        for item in file_items:
            if not item.startswith("_"):
                if item.endswith("_"):
                    returned_path.append(item[:-1])
                else:
                    returned_path.append(item)

        # Build path from items excluding prefix and suffix
        return "/" + "/".join(returned_path)

    def _compute_nextjs_webpack(self, filename: str) -> Optional[str]:
        """
        Computes the route for Next.js Webpack plugin.
        Doc: https://nextjs.org/docs/app/building-your-application/routing
        """
        path_items = Path(filename).parts

        # Check if contains at least 2 parts (prefix and suffix)
        if len(path_items) < 2:
            return None

        # Check if prefix is present and suffix is a file type
        if path_items[0] != self._prefix or not self._is_file(path_items[-1]):
            return None

        # Build path from items excluding prefix and suffix
        return "/" + "/".join(path_items[1:-1])

    def _compute_nuxt(self, filename: str) -> Optional[str]:
        """
        Computes the route for Nuxt plugin.
        Doc: https://nuxt.com/docs/getting-started/routing
        """
        path_items = Path(filename).parts

        # Check if contains at least 2 parts (prefix and suffix)
        if len(path_items) < 2:
            return None

        # Check if prefix is present and suffix is a file type that has .vue extension
        if path_items[0] != self._prefix or not self._is_file(path_items[-1], ["vue"]):
            return None

        # Remove .vue from last path item
        path_items = list(path_items)
        path_items[-1] = path_items[-1][:-4]

        # Drop file index if exists
        if path_items[-1] == "index":
            path_items.pop()

        # Build path from items excluding prefix
        return "/" + "/".join(path_items[1:])

    def _compute_solidstart(self, filename: str) -> Optional[str]:
        """
        Computes the route for SolidtStart plugin.
        Doc: https://docs.solidjs.com/solid-start/building-your-application/routing#file-based-routing
        """
        path_items = Path(filename).parts

        # Check if contains at least 3 parts (2 prefix and suffix)
        if len(path_items) < 3:
            return None

        # Check if 2 prefix is present
        if path_items[0] != self._prefix[0] or path_items[1] != self._prefix[1]:
            return None

        # Check if suffix is a file that with valid extensions
        if not self._is_file(path_items[-1], extensions=["tsx", "ts", "jsx", "js"]):
            return None

        # Remove route groups and renamed indices, ie remove character inside parenthesis and itself
        returned_items = [re.sub(r"\(.*?\)", "", item) for item in path_items]

        # Get the file name without extension
        file = returned_items[-1]
        file = file[: file.rfind(".")]
        returned_items[-1] = file

        # Remove index file if exists
        if returned_items[-1] == "index":
            returned_items.pop()

        # Build path from items excluding prefix and suffix
        return "/" + "/".join([item for item in returned_items[2:] if item != ""])

    def _compute_sveltekit(self, filename: str) -> Optional[str]:
        """
        Computes the route for SvelteKit plugin.
        Doc: https://svelte.dev/docs/kit/routing
        """
        path_items = Path(filename).parts

        # Check if contains at least 3 parts (2 prefix and suffix)
        if len(path_items) < 3:
            return None

        # Check if 2 prefix is present
        if path_items[0] != self._prefix[0] or path_items[1] != self._prefix[1]:
            return None

        # Check if suffix is a file that starts with "+"
        if not self._is_file(path_items[-1]) or not path_items[-1].startswith("+"):
            return None

        # Build path from items excluding 2 prefix and suffix
        return "/" + "/".join(path_items[2:-1])

    def get_from_filename(self, filename: str) -> Optional[str]:
        """
        Computes the route.
        Args:
            filename (str): The file path to compute the route from.

        Returns:
            Optional[str]: The computed route or None if invalid.
        """
        try:
            return self._compute_from_filename(filename)
        except Exception as e:
            log.error(
                f"Uncaught error during AssetRoute path compute: {e}", exc_info=True
            )
            return None


def get_extension(filename: str) -> str:
    """
    Gets the file extension of the file without the dot
    """
    # At times file can be something like './index.js + 12 modules', only keep the real filepath
    filename = filename.split(" ")[0]
    # Retrieve the file extension with the dot
    _, file_extension = os.path.splitext(filename)
    # Return empty string if file has no extension
    if not file_extension or file_extension[0] != ".":
        return ""
    # Remove the dot in the extension
    file_extension = file_extension[1:]
    # At times file can be something like './index.js?module', remove the ?
    file_extension = file_extension.split("?")[0]

    return file_extension


def split_by_delimiter(
    s: str,
    delimiter: str,
    escape_open: Optional[str] = None,
    escape_close: Optional[str] = None,
) -> List[str]:
    """
    Splits a string based on a specified delimiter character, optionally respecting escape delimiters.

    Parameters:
    ----------
    s : str
        The input string to split.
    delimiter : str
        The character used to split the string. Must be a single character.
    escape_open : Optional[str], default=None
        The character indicating the start of an escaped section.
        If provided, must be a single character.
    escape_close : Optional[str], default=None
        The character indicating the end of an escaped section.
        If provided, must be a single character.

    Returns:
    -------
    List[str]
        A list of substrings obtained by splitting `s` at occurrences of `delimiter`,
        unless the delimiter is within an escaped section.
        Returns an empty list if input parameters are invalid.
    """
    # Error handling for invalid parameters
    if not s:
        return []
    if not isinstance(delimiter, str) or len(delimiter) != 1:
        return []
    if (
        escape_open is not None
        and (not isinstance(escape_open, str) or len(escape_open) != 1)
    ) or (
        escape_close is not None
        and (not isinstance(escape_close, str) or len(escape_close) != 1)
    ):
        return []
    if (escape_open is None) != (escape_close is None):  # Only one of them is None
        return []
    if delimiter == escape_open or delimiter == escape_close:
        return []

    result = []
    buffer = []
    inside_escape = 0

    for char in s:
        if char == escape_open:
            inside_escape += 1
            if inside_escape == 1:
                continue  # Skip adding the opening escape character
        elif char == escape_close:
            inside_escape -= 1
            if inside_escape == 0:
                continue  # Skip adding the closing escape character
            elif inside_escape < 0:
                return []
        elif char == delimiter and inside_escape == 0:
            # Split here if not inside escape brackets
            result.append("".join(buffer))
            buffer = []
            continue

        buffer.append(char)

    if buffer or s[-1] == delimiter:
        result.append("".join(buffer))

    if inside_escape != 0:
        return []

    return result
