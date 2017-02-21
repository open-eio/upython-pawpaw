import time, socket

import gc

try:
    import sys
    from sys import print_exception #micropython specific
except ImportError:
    import traceback
    print_exception = lambda exc, file_: traceback.print_exc(file=file_)


try:
    from collections import OrderedDict
except ImportError: 
    from ucollections import OrderedDict #micropython specific
    
try:
    import json
except ImportError:
    import ujson as json #micropython specific
    
    
from .template_engine import Template, LazyTemplate
from .http_connection_reader import HttpConnectionReader
from .http_connection_writer import HttpConnectionWriter

DEBUG = False
DEBUG = True
################################################################################
# Classes

#-------------------------------------------------------------------------------
class HttpServer(object):
    timeout = None
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 5
    allow_reuse_address = True
    rbufsize = -1
    wbufsize = -1
    
    handler_registry = OrderedDict()

    def __init__(self, server_address, app,
                 init_socket = True,
                 timeout = None, #default is BLOCKING
                 ):
        #BaseServer.__init__(self, server_address, RequestHandlerClass)
        self.server_address = server_address
        self.app = app
        self.__is_shut_down = None #FIXME threading.Event()
        self.__shutdown_request = False
        self._timeout = timeout
        self.socket = socket.socket(self.address_family,
                                    self.socket_type)
        if init_socket:
            self.init_socket()
    
    def init_socket(self):
        self.socket.settimeout(self._timeout)
        try:
            self.server_bind()
            self.server_activate()
        except:
            self.socket.close()
            raise
        
    def server_bind(self):
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        host, port = self.server_address
        addr = socket.getaddrinfo(host,port)[0][-1]
        self.socket.bind(addr)
        self.server_address = addr

    def server_activate(self):
        try:
            self.socket.listen(self.request_queue_size)
        except OSError as exc:
            gc.collect()
            import errno
            if exc.args[0] == errno.ENOMEM:
                #listener is already registered
                print("WARNING: handling %s" % exc)
                self.socket.close()
                self.init_socket()
            else:
                raise
        
    def serve_forever(self, poll_interval=0.5):
        #FIXME self.__is_shut_down.clear()
        try:
            while not self.__shutdown_request:
                self.handle_request()
        finally:
            self.__shutdown_request = False
            #FIXME self.__is_shut_down.set()
    
    def shutdown(self):
        self.__shutdown_request = True
        #FIXME self.__is_shut_down.wait()

    def handle_request(self):
        client_sock = None
        client_address = None
        conn_rfile = None
        conn_wfile = None
        request = None
        try:
            phase = "listening for connection"
            client_sock, client_address = self.socket.accept()
            phase = "accepted connection from '%s'" % (client_address,)
            conn_rfile = client_sock.makefile('rb', self.rbufsize)
            conn_wfile = client_sock.makefile('wb', self.wbufsize)
            #-------------------------------------------------------------------
            #reading request phase
            #on micropython makefile does nothing returns a usocket.socket obj
            conn_reader = HttpConnectionReader(conn_rfile, client_address)
            phase = 'reading request'
            request = conn_reader.parse_request()
            #-------------------------------------------------------------------
            # handler lookup phase
            phase = 'handler lookup path'
            handler = None
            if not request is None:
                meth_paths = self.app.path_handler_registry.get(request.method, {})
                handler = meth_paths.get(request.path)
            #could not match a path directly
            if handler is None:
                # try matching against all regex handlers
                phase = 'handler lookup regex'
                match = None
                meth_regexs = self.app.regex_handler_registry.get(request.method, {})
                for repr_regex, data in meth_regexs.items():
                    regex, h = data
                    match = regex.match(request.path)
                    if not match is None:
                        request.match = match
                        handler = h
                        break
                else:
                    #default no other handler matched
                    handler = self.app.path_handler_registry['DEFAULT']
            #-------------------------------------------------------------------
            # response phase
            conn_writer = HttpConnectionWriter(conn_wfile,request)
            phase = 'handling response'
            if DEBUG:
                print("INSIDE 'http_server.handle_request' during %s:" % phase)
                print("\trequest: %s" % request)
            handler(conn_writer)
            return True  #signify that a request was successfully handled
        except OSError as exc:
            import errno
            if exc.args[0] == errno.ETIMEDOUT:
                #if DEBUG:
                #    print("HttpServer.handle_request: timedout during {}".format(phase))
                return False  #signify that no request handled
            else:
                raise
        except Exception as exc:
            buff = []
            buff.append("Context: Exception caught in 'HttpServer.handle_request' during {}".format(phase))
            if not request is None:
                buff.append("Request:")
                for line in request.str_lines():
                    buff.append("    %s" % line)
                buff.append("") #final newline
            msg = "\n".join(buff)
            #print out message and exception/traceback
            print("*"*40,file=sys.stderr)
            print("* EXCEPTION", file=sys.stderr)
            print("-"*40,file=sys.stderr)
            print(msg, file = sys.stderr)
            print_exception(exc, sys.stderr)
            print("*"*40,file=sys.stderr)
            #log it as well
            logger = self.app.get_logger()
            with logger as entry:
                entry.write(msg)
                entry.write_exception(exc)
        finally:
            if not conn_rfile is None:
                conn_rfile.close()
            if not conn_rfile is None:
                conn_wfile.close()
            if not client_sock is None:
                client_sock.close()
            gc.collect()
