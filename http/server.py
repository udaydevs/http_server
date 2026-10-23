"""HTTP server built directly on top of TCP sockets."""
from __future__ import annotations
import os
from pathlib import Path
import socket
import io
import logging
import mimetypes
from http import HTTPStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(
    'http-server'
)

class SecurityException(Exception):
    pass

class UDServer:
    """TCP server that accepts connections and delegates each request."""

    def __init__(
        self,
        socket_address: tuple[str, int],
        request_handler: UDRequestHandler
    ) -> None:
        """Create, bind, and start listening on the given socket address."""
        self.request_handler = request_handler
        self.sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        self.sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )
        self.sock.bind(socket_address)

        logger.info('Started Serving')

        self.sock.listen()

    def serve_forever(self):
        """Accept client connections and handle them one at a time."""
        while True:
            conn, addr = self.sock.accept()

            with conn:
                logger.info('Connected to %s', {addr})

                request_stream = conn.makefile('rb')
                response_stream = conn.makefile('wb')

                self.request_handler(
                    request_stream=request_stream,
                    response_stream=response_stream
                )

            logger.info('Connection closed to %s', {addr})

    def __enter__(self) -> 'UDServer':
        """Return the server for use as a context manager."""
        return self

    def __exit__(self, *args) -> None:
        """Close the listening socket when leaving the context."""
        self.sock.close()


class UDRequestHandler:
    """Parse one HTTP request and write the matching response."""

    def __init__(
        self,
        request_stream: io.BufferedIOBase,
        response_stream: io.BufferedIOBase,
    ):
        """Store request streams and immediately handle the request."""
        self.request_stream = request_stream
        self.response_stream = response_stream

        self.command = ''
        self.path = ''

        self.header = {
            'Content-Type': 'text/uday',
            'Content-Length': '0',
            'Connection': 'close'
        }

        self.data = ''

        self.handler()

    def _parse_request(self):
        """Read the request line and headers from the client stream."""
        logger.info('Parsing the request')

        requestline = self.request_stream.readline().decode()
        requestline = requestline.rstrip('\r\n')
        if len(requestline) > 8 * 1024:
            print(len(requestline))
            return HTTPStatus(401).phrase

        logger.info(requestline)

        self.command = requestline.split(' ')[0]
        self.path = requestline.split(' ')[1]

        headers = {}

        line = self.request_stream.readline().decode()

        while line not in ('\r\n', '\n', '\r', ''):
            header = line.rstrip('\r\n').split(': ')
            headers[header[0]] = header[1]

            line = self.request_stream.readline().decode()

        logger.info(headers)

    def handle_GET(self) -> None:
        '''
        Writes headers and the file to the socket.
        '''
        self.handle_HEAD()

        with open(self.path, 'rb') as f:
            body = f.read()

        self.response_stream.write(body)
        self.response_stream.flush()  # flush to send data

    def handle_POST(self) ->None:
        """Send response headers followed by the request body"""
        self.handle_HEAD()

    def handle_HEAD(self) -> None:
        """
        Send response headers for the requested file.
        It ensures that HEAD does not contains response body
        """

        self._write_response_line(200)

        self._write_headers(
            **{
                'Content-Type' : mimetypes.guess_type(self.path,strict=True)[0],
                'Content-Length': os.path.getsize(self.path)
            }
        )

        self.response_stream.flush()

    def handler(self) -> None:
        """Route the parsed request to the supported method handler."""

        # Anything but GET and HEAD will return 405
        # POST will return 403
        # Parse the request to populate

        self._parse_request()

        if not self._validate_path():
            return self._return_404()

        if self.command not in ('GET', 'HEAD', 'POST'):
            return self._return_405()

        command = getattr(
            self,
            f'handle_{self.command}'
        )

        command()

    def _write_response_line(self, status_code: int) -> None:
        """Write the HTTP status line for a response."""
        response_line = f'HTTP/1.1 {status_code} {HTTPStatus(status_code).phrase} \r\n'

        logger.info(response_line.encode())

        self.response_stream.write(response_line.encode())

    def _write_headers(self, **kwargs):
        """Write default headers merged with response-specific values."""
        headers_copy = self.header.copy()
        headers_copy.update(**kwargs)

        headers_lines = '\r\n'.join(
            f'{k}:{v}' for k, v in headers_copy.items()
        )

        logger.info(headers_lines.encode())

        self.response_stream.write(headers_lines.encode())
        self.response_stream.write(b'\r\n\r\n')

    def _validate_path(self) -> bool:
        """
        Resolve the request path and validation to 
        prevent from attacks like path traversal
        """
        filename = os.getcwd()
        print(filename)
        working_path = 'http/index.html'
        if os.path.isdir(filename):
            path = Path(
                os.path.join(filename,working_path)
                ).resolve() #it will resolve the path to absolute path
            print(path)
            resolved_path = (filename/path).resolve() #construct the absolute path requested
            if not str(resolved_path).startswith(str(path)):
                raise SecurityException(
                    "Invalid path: Attempt to access a file outside the allowed workspace."
                    )
            self.path = resolved_path

            logger.info(self.path)

        elif os.path.isfile(self.path):
            pass

        if os.path.exists(self.path):
            return True

        return False

    def _return_404(self) -> None:
        """Send a 404 Not Found response."""

        self._write_response_line(404)
        self._write_headers()

    def _return_405(self) -> None:
        """Send a 405 Method Not Allowed response."""

        self._write_response_line(405)
        self._write_headers()

    def _return_403(self) -> None:
        """Send a 403 Forbidden response."""

        self._write_response_line(403)
        self._write_headers()


with UDServer(('0.0.0.0', 8000), UDRequestHandler) as http:
    logger.info('Serving at port 8000')
    http.serve_forever()
