import gzip
import importlib.metadata
from typing import IO


class GZipStreamReader:
    def __init__(self, fileobj: IO[bytes]):
        self.data = fileobj

    def read(self, size: int = -1, /) -> bytes:
        curr_data = self.data.read(size)

        if not curr_data:
            return b""

        return gzip.compress(curr_data)


def zstd_decoded_by_default() -> bool:
    try:
        version = importlib.metadata.version("urllib3")
    except importlib.metadata.PackageNotFoundError:
        return False

    if version < "2.0.0":
        return False

    distribution = importlib.metadata.metadata("urllib3")
    if requires_dist := distribution.get_all("Requires-Dist"):
        for req in requires_dist:
            if "[zstd]" in req:
                return True

    return False
