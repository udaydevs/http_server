"""
Building my own http server from scratch
"""
from asyncio.log import logger
from http import HTTPStatus
import logging
import os
import socket
import io

HOST = '127.0.0.1'
PORT = 6666


logger = logging.getLogger('http-server')

class UDRequestHandler:
    def __init__(
            self,
            request_stream: io.BufferedIOBase,
            response_stream: io.BufferedIOBase,
        ):
        self.request_stream = request_stream
        self.response_stream = response_stream
        self.command = ''
        self.path = ''
        self.header = {
            'Content-Type' : 'text/html',
            'Content-Length' : '0',
            'Connection' : 'close'
        }
        self.data = ''
        self.handler()

    def _parse_request(self):
        logger.info('Parsing the request')
        requestline = self.request_stream.readline().decode()
        requestline = requestline.rstrip('\r\n')
        logger.info(requestline)

        self.command = requestline.split(' ')[0]
        self.path = requestline.split(' ')[1]

        headers = {}
        line = self.request_stream.readline().decode()
        while line not in ('\r\n' , '\n', '\r', ''):
            header = line.rstrip('\r\n').split(': ')
            headers[header[0]] = header[1]
            line = self.request_stream.readline().decode()

        logger.info(headers)

    def handle_GET(self)-> None:
        '''Writes Header and file to the socket'''
        self.handle_HEAD()

        with open(self.path ,'rb') as f:
            body = f.read()

        self.response_stream.write(body)
        self.response_stream.flush() #flush to send data

    def handle_HEAD(self) -> None:
        '''Writes header to the socket'''
        self._write_response_line(200)
        self._write_headers(
                **{
                    'Content_Length' : os.path.getsize(self.path)
                }
            )
        self.response_stream.flush() #flush to send the response

    def handler(self) -> None:
                    '''This will Handle the request'''
                    #Anything but GET and HEAD will return 405
                    #POST will return 403
                    #Parse the request to populate
                    self._parse_request()
            
                    if not self._validate_path():
                        return self._return_404()
            
                    if self.command == 'POST':
                        return self._return_403()
            
                    if self.command not in ('GET', 'HEAD'):
                        return self._return_405()
            
                    command = getattr(self, f'handle_{self.command}')
                    command()
            

            
    def _write_response_line(self, status_code : int) -> None:
                        response_line = f'HTTP/1.1 {status_code} NOTFOUND \r\n'
                        logger.info(response_line.encode())
                        self.response_stream.write(response_line.encode())
            
    def _write_headers(self, *args, **kwargs):
                        headers_copy = self.header.copy()
                        headers_copy.update(**kwargs)
                        headers_lines = '\r\n'.join(
                             f'{k}:{v}' for k, v in headers_copy.items()
                        )
                        logger.info(headers_lines.encode())
                        self.response_stream.write(headers_lines.encode())
                        #Marking the ends of the headers
                        self.response_stream.write(b'\r\n\r\n')
            
    def _validate_path(self) -> bool:
                            '''
                            It validates the path. Returns True if the path is valid, otherwise False
                            '''
                            #Path can either be file or dictonary
                            #if the path is dictonary, look for index.html
                            #if it's file, serve it 
                            self.path = os.path.join(os.getcwd(), self.path.lstrip('/'))
                            if os.path.isdir(self.path):
                                self.path = os.path.join(self.path , 'index.html')
                            elif os.path.isfile(self.path):
                                pass
                    
                            if os.path.exists(self.path):
                                return True
                    
                            return False
                    
    def _return_404(self) -> None:
                '''NOT FOUND'''
                self._write_response_line(404)
                self._write_headers()
                            
    def _return_405(self) -> None:
                '''METHOD NOT ALLOWED'''
                self._write_response_line(405)
                self._write_headers()
                            
    def _return_403(self) -> None:
                '''FORBIDDEN'''
                self._write_response_line(403)
                self._write_headers()


"""Now we are going to build our own tcp server"""
class UDServer:
    def __init__(
            self, 
            socket_address : tuple[str, int],
            request_handler: UDRequestHandler
        ) -> None:
        self.request_handler = request_handler
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(socket_address)
        logger.info('Started Serving')
        self.sock.listen()

    def serve_forever(self):
        while True:
            conn, addr = self.sock.accept()
            with conn:
                logger.info(f'Connected to {addr}')
                request_stream = conn.makefile('rb')
                response_stream = conn.makefile('wb')
                self.request_handler(
                    request_stream = request_stream,
                    response_stream = response_stream
                )
            logger.info(f'Connection closed to {addr}')

    def __enter__(self) -> 'UDServer':
        return self

    def __exit__(self, *args) -> None:
        self.sock.close()


with UDServer(('0.0.0.0' , 8000), UDRequestHandler) as http:
    logger.info(f'Serving at port 8000')
    http.serve_forever()