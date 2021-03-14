import http.server as BaseHTTPServer
import json
import os.path
import socket
import threading
import time
import urllib.request
import urllib.error
from http.server import SimpleHTTPRequestHandler


class FakeServer(object):
    DEFAULT_PORT = 57575
    DEFAULT_RESPONSE = "Default Response"
    DEFAULT_RESPONSE_CODE = 200
    DEFAULT_RESPONSE_TYPE = "text/xml"
    FILE_DIR = "./test/helpers/requests/"
    RESPONSE_FILE = FILE_DIR + "fake-http-server-response.txt"
    RESPONSE_CODE_FILE = FILE_DIR + "fake-http-server-response-code.txt"
    REQUEST_FILE = FILE_DIR + "fake-http-server-request.txt"
    WAIT_UNTIL_READY_DELAY = 0.1
    timeout_delay = 0

    def __init__(self, port=DEFAULT_PORT):
        self.port = port
        self._httpd = None
        self._server_thread = None
        self._serve_in_loop = False
        self._server_started = False
        self._ready_to_serve = False

    class ServerStateException(Exception):
        pass

    class RequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, request, client_address, server):
            self._lock = threading.Lock()
            self._code = FakeServer.DEFAULT_RESPONSE_CODE
            self._response = FakeServer.DEFAULT_RESPONSE
            self._start_request_handler(request, client_address, server)

        def _start_request_handler(self, request, client_address, server):
            try:
                SimpleHTTPRequestHandler.__init__(self, request, client_address, server)
            except socket.error:
                pass

        def do_POST(self):
            with self._lock:
                self.log_message("POST: Command: %s Path: %s Headers: %s", self.command, self.path, self.headers.items())
                with open(FakeServer.REQUEST_FILE, "w") as request_file:
                    request_file.write(json.dumps({"headers": self.headers, "body": self._get_request_body()}))
                self.write_response()
        
        def do_GET(self):
            with self._lock:
                self.log_message("GET: Command: %s Path: %s  Headers: %s", self.command, self.path, self.headers.items())
                with open(FakeServer.REQUEST_FILE, "w") as request_file:
                    request_file.write(self.path + "\n" + str(self.headers))
                self._execute_and_reset_delay()
                self.write_response()

        def read_file_or_default_to(self, file_path, default_value):
            if os.path.exists(file_path):
                with open(file_path, "r") as file:
                    content = file.read().rstrip()
                return content
            return default_value
    
        def write_response(self, response_type=""):
            response_type = response_type or FakeServer.DEFAULT_RESPONSE_TYPE
            self._update_response()
            self.send_response(self._code)
            self.send_header("Content-type", response_type)
            self.send_header("Content-length", str(len(self._response)))
            self.end_headers()
            self.wfile.write(self._response.encode("utf-8"))

        def _update_response(self):
            self._response = self.read_file_or_default_to(FakeServer.RESPONSE_FILE, FakeServer.DEFAULT_RESPONSE)
            self._code = int(self.read_file_or_default_to(FakeServer.RESPONSE_CODE_FILE, FakeServer.DEFAULT_RESPONSE_CODE))

        def _get_request_body(self):
            if "content-length" in self.headers:
                length = int(self.headers["content-length"])
                return self.rfile.read(length)
            return ""

        def _execute_and_reset_delay(self):
            if FakeServer.timeout_delay > 0:
                time.sleep(FakeServer.timeout_delay)
                FakeServer.timeout_delay = 0

    def start_server(self):
        if not self._server_started:
            self._httpd = BaseHTTPServer.HTTPServer(("127.0.0.1", int(self.port)), self.RequestHandler)
            self._server_started = True
        else:
            raise self.ServerStateException({"message": "The server is already running.", "state": "on"})

    def stop_server(self):
        if self._server_started:
            if self._ready_to_serve and self._serve_in_loop:
                self._httpd.shutdown()
                self._serve_in_loop = False
            elif self._ready_to_serve:
                urllib.request.urlopen(self.get_url()).read()  # generate empty request required to close listener
            self._ready_to_serve = False
            self._httpd.server_close() 
            self._server_started = False
            self.__clean_files()
        else:
            raise self.ServerStateException({"message": "The server is already stopped.", "state": "off"})

    def is_alive(self):
        return self._server_started

    def is_ready_to_process(self):
        return self._ready_to_serve

    def get_url(self):
        return "http://localhost:" + str(self.port) + "/"

    def serve_once(self):
        self.__start_as_daemon(self.__serve_once)

    def serve_forever(self):
        self.__start_as_daemon(self.__serve_forever)

    def __start_as_daemon(self, target_function):
        if self._server_started and not self._ready_to_serve:
            self._server_thread = threading.Thread(target=target_function)
            self._server_thread.setDaemon(True)
            self._server_thread.start()
            while not self._ready_to_serve:
                time.sleep(FakeServer.WAIT_UNTIL_READY_DELAY)
        else:
            if not self._server_started:
                raise self.ServerStateException({"message": "Make sure to start server before processing requests.", "state": "off"})
            elif self._ready_to_serve:
                raise self.ServerStateException({"message": "The server is already listening for requests.", "state": "listening"})

    def __serve_once(self):
        self._ready_to_serve = True
        self._httpd.handle_request()
        self._ready_to_serve = False

    def __serve_forever(self):
        if self._server_started and not self._ready_to_serve:
            self._ready_to_serve = True
            self._serve_in_loop = True
            self._httpd.serve_forever()

    def set_expected_response(self, content, code):
        try:
            self._set_response_content(content)
            self._set_response_code(code)
        except:
            raise self.ServerStateException("Cannot create response files, check write permissions for " + self.__class__.FILE_DIR)

    def _set_response_content(self, content):
        with open(FakeServer.RESPONSE_FILE, "w") as response_file:
            response_file.write(str(content))

    def _set_response_code(self, code):
        with open(FakeServer.RESPONSE_CODE_FILE, "w") as response_code_file:
            response_code_file.write(str(code))

    @classmethod
    def set_timeout_delay(cls, delay):
        cls.timeout_delay = delay + 0.1  # add 0.1 to ensure that delay will trigger when exact timeout value is provided

    def __clean_files(self):
        try:
            os.remove(FakeServer.RESPONSE_FILE)
            os.remove(FakeServer.RESPONSE_CODE_FILE)
            os.remove(FakeServer.REQUEST_FILE)
        except:
            pass  # Don't raise exceptions if cannot delete files
