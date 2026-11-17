"""Measure download throughput using ten sequential HTTP requests."""

import argparse
import sys
from http.client import HTTPException
from time import perf_counter
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

REQUEST_COUNT = 10
CHUNK_SIZE = 64 * 1024
TIMEOUT = 30


def download(url: str) -> tuple[int, float]:
    request = Request(url, headers={"Accept-Encoding": "identity"})
    size = 0
    started = perf_counter()
    with urlopen(request, timeout=TIMEOUT) as response:
        if response.status != 200:
            raise ValueError(f"Expected HTTP 200, got {response.status}")
        while chunk := response.read(CHUNK_SIZE):
            size += len(chunk)
        # A chunked response is framed by Transfer-Encoding, not Content-Length.
        expected = response.headers.get("Content-Length")
        if expected is not None and not response.headers.get("Transfer-Encoding"):
            if size != int(expected):
                raise ValueError("Incomplete response body")
    return size, perf_counter() - started


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure download speed with 10 sequential HTTP requests."
    )
    parser.add_argument("url", help="HTTP(S) URL of a file to download")
    args = parser.parse_args()
    try:
        parsed = urlsplit(args.url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            parser.error("URL must start with http:// or https:// and include a host")
        parsed.port  # Validate a supplied port before making requests.
    except ValueError as error:
        parser.error(str(error))

    total_bytes = 0
    total_seconds = 0.0
    for number in range(1, REQUEST_COUNT + 1):
        try:
            size, elapsed = download(args.url)
        except (URLError, OSError, HTTPException, ValueError) as error:
            print(f"Request {number}/{REQUEST_COUNT} failed: {error}", file=sys.stderr)
            return 1
        total_bytes += size
        total_seconds += elapsed
        print(f"Request {number}/{REQUEST_COUNT}: {size} bytes, {elapsed:.3f} s")

    print(f"Average request time: {total_seconds / REQUEST_COUNT:.3f} s")
    print(f"Total downloaded: {total_bytes} bytes ({total_bytes / 1_000_000:.3f} MB)")
    print(f"Download speed: {total_bytes * 8 / total_seconds / 1_000_000:.3f} Mbit/s")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nMeasurement interrupted.", file=sys.stderr)
        sys.exit(130)
