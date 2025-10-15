from typing import Iterable


class HttpResponse:
    """HttpResponse with fileobject methods."""

    def __init__(self) -> None:
        """Class initialization."""

        ...

    def read(
        self,
        size: int | None = None,
    ) -> bytes:
        """Read data from the HTTP response.

        Args:
            size: Number of bytes to read.
            If None or not specified, reads all available data.

        Returns:
            Bytes read from the response.
        """

        ...

    def read1(self) -> bytes:
        """Read a single byte from the HTTP response.

        Returns:
            Single byte as bytes object.
        """

        ...

    def get_status(self) -> int | None:
        """Get the HTTP status code.

        Returns:
            HTTP status code or None if not available.
        """

        ...

    def get_headers(self) -> dict[str, str] | None:
        """Get all response headers.

        Returns:
            Dictionary of header names (lowercase)
            to values, or None if not available.
        """

        ...

    def get_header(self, name: str) -> str | None:
        """Get a specific response header.

        Args:
            name: Header name (case-insensitive).

        Returns:
            Header value or None if header doesn't exist.
        """

        ...

    def get_content_length(self) -> int | None:
        """Get the content length from response headers.

        Returns:
            Content length in bytes or None if not specified.
        """

        ...

    def is_success(self) -> bool:
        """Check if the response indicates success (2xx status code).

        Returns:
            True if status code is in 200-299 range.
        """

        ...

    def is_redirect(self) -> bool:
        """Check if the response indicates a redirect (3xx status code).

        Returns:
            True if status code is in 300-399 range.
        """

        ...

    def is_client_error(self) -> bool:
        """Check if the response indicates a client error (4xx status code).

        Returns:
            True if status code is in 400-499 range.
        """

        ...

    def is_server_error(self) -> bool:
        """Check if the response indicates a server error (5xx status code).

        Returns:
            True if status code is in 500-599 range.
        """

        ...

    def get_content_type(self) -> str | None:
        """Get the Content-Type header value.

        Returns:
            Content-Type value or None if not specified.
        """

        ...

    def get_url(self) -> str | None:
        """Get the final URL of the response (after redirects).

        Returns:
            URL string or None if not available.
        """

        ...

    def seek(self, pos: int) -> None:
        """Seek to a position in the response stream.

        Args:
            pos: Position to seek to (only position 0 is supported).

        Raises:
            IOError: If seeking is not allowed or position is not 0.
        """

        ...

    def seekable(self) -> bool:
        """Check if the response stream supports seeking.

        Returns:
            True if seeking to position 0 is allowed.
        """

        ...

    def close(self) -> None:
        """Close the response and release resources."""

        ...

    def is_closed(self) -> bool:
        """Check if the response is closed.

        Returns:
            True if response is closed.
        """

        ...

    def get_info(self) -> dict[str, str]:
        """Get comprehensive information about the response.

        Returns:
            Dictionary containing response metadata.
        """

        ...

    def tell(self) -> int:
        """Get the current read position in the response stream.

        Returns:
            Current position in bytes.
        """

        ...


class HttpSession:
    """HttpSession with post method only."""

    def __init__(
        self,
        timeout: float | int | None,
    ) -> None:
        """Initialize an HTTP session.

        Args:
            timeout: Request timeout in seconds. Default is 30 seconds.

        Raises:
            RuntimeError: If HTTP client creation fails.
        """

        ...

    def post(
        self,
        url: str,
        headers: dict[str, str] | None,
        params: dict[str, str] | None,
        data: bytes | Iterable[bytes | bytearray] | None,
        timeout: float | int | None,
    ) -> HttpResponse:
        """Send a POST request.

        Args:
            url: Target URL.
            headers: HTTP headers as key-value pairs.
            params: URL parameters as key-value pairs.
            data: Request body data. Can be:
                - bytes
                - list of bytes objects
                - byte array
                - iterable/generator yielding bytes
            timeout: Request timeout in seconds (overrides session timeout).

        Returns:
            HttpResponse object.

        Raises:
            IOError: If HTTP request fails.
            TypeError: If data type is not supported.
        """

        ...

    def post_stream(
        self,
        url: str,
        headers: dict[str, str] | None,
        params: dict[str, str] | None,
        data: bytes | Iterable[bytes | bytearray] | None,
        timeout: float | int | None,
    ) -> HttpResponse:
        """Send a POST request (alias for post method).

        Args:
            url: Target URL.
            headers: HTTP headers as key-value pairs.
            params: URL parameters as key-value pairs.
            data: Request body data.
            timeout: Request timeout in seconds.

        Returns:
            HttpResponse object.
        """

        ...

    def close(self) -> None:
        """Close the HTTP session and release resources.

        This method should be called when the session is no longer needed
        to properly clean up connections and resources.
        """

        ...
