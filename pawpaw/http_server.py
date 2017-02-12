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

    def __init__(self, server_address, app, bind_and_activate=True):
        #BaseServer.__init__(self, server_address, RequestHandlerClass)
        self.server_address = server_address
        self.app = app
        self.__is_shut_down = None #FIXME threading.Event()
        self.__shutdown_request = False
        
        self.socket = socket.socket(self.address_family,
                                    self.socket_type)
        if bind_and_activate:
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
        self.socket.listen(self.request_queue_size)
        
    def serve_forever(self, poll_interval=0.5):
        #FIXME self.__is_shut_down.clear()
        try:
            while not self.__shutdown_request:
                self._handle_request_noblock()
        finally:
            self.__shutdown_request = False
            #FIXME self.__is_shut_down.set()
    
    def shutdown(self):
        self.__shutdown_request = True
        #FIXME self.__is_shut_down.wait()

    def _handle_request_noblock(self):
        if DEBUG:
            print("INSIDE HttpServer._handle_request_noblock")
            try:
                from micropython import mem_info
                mem_info()
            except ImportError:
                pass
        client_sock = None
        client_address = None
        conn_rfile = None
        conn_wfile = None
        request = None
        try:
            phase = "listening for connection"
            if DEBUG:
                print("\t%s" % phase)
            client_sock, client_address = self.socket.accept()
            phase = "accepted connection from '%s'" % (client_address,)
            if DEBUG:
                print("\t%s" % phase)
            conn_rfile = client_sock.makefile('rb', self.rbufsize)
            conn_wfile = client_sock.makefile('wb', self.wbufsize)
            #-------------------------------------------------------------------
            #reading request phase
            #on micropython makefile does nothing returns a usocket.socket obj
            conn_reader = HttpConnectionReader(conn_rfile, client_address)
            phase = 'reading request'
            if DEBUG:
                print("\t%s" % phase)
            request = conn_reader.parse_request()
            #-------------------------------------------------------------------
            # handler lookup phase
            phase = 'handler lookup'
            if DEBUG:
                print("\t%s" % phase)
            handler = None
            if not request is None:
                key = "%s %s" % (request.method, request.path)
                if DEBUG:
                    print("\t\tkey: %r" % key)
                handler = self.app.handler_registry.get(key)
            if handler is None:
                handler = self.app.handler_registry['DEFAULT']
            #-------------------------------------------------------------------
            # response phase
            conn_writer = HttpConnectionWriter(conn_wfile,request)
            phase = 'handling response'
            if DEBUG:
                print("\t%s" % phase)
                print("\t\thandler: %s" % handler)
            handler(conn_writer)
        except Exception as exc:
            buff = []
            buff.append("Context: Exception caught in 'HttpServer._handle_request_noblock' during {}".format(phase))
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
