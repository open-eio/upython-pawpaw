import time, socket

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
    
from . import urllib_parse

DEBUG = False
DEBUG = True
################################################################################
# Classes
class HttpRequest(object):
    __slots__ = 'method','path','args','headers','client_address', 'body'
    def str_lines(self):
        buff = []
        for attr in self.__slots__:
            buff.append("%s: %s" % (attr, getattr(self,attr)))
        return buff
    def __str__(self):
        return "\n".join(self.str_lines())

class HttpConnectionReader(object):
    def __init__(self, conn_rfile, client_address):
        self._conn_rfile = conn_rfile
        self.client_address = client_address

    def parse_request(self):
        global DEBUG
        if DEBUG:
            print("INSIDE HttpConnectionReader.parse_request")
            try:
                from micropython import mem_info
                mem_info()
            except ImportError:
                pass
        # self.rfile is a file-like object created by the handler;
        # we can now use e.g. readline() instead of raw recv() calls
        #parse the request header
        request_line = str(self._conn_rfile.readline(),'utf8').strip()
        if DEBUG:
            print("CLIENT: %s" % request_line)
        try:
            method, req_url, protocol = request_line.split()
        except ValueError:
            self.handle_malformed_request_line(request_line)
            return None
        req = urllib_parse.urlparse(req_url)
        #split off any query params if they exist
        params = urllib_parse.parse_qs(req.query)
        #read the remaining request headers
        headers = OrderedDict()
        while True:
            line = str(self._conn_rfile.readline(),'utf8').strip()
            if DEBUG:
                print("CLIENT req.headers: %r" % line)
            if not line or line == '\r\n':
                break
            key, val = line.split(':',1)
            headers[key] = val
        #check the method
        body = None
        if method == "POST": #there might be a message body
            clen = headers.get('Content-Length')
            if not clen is None:
                body = str(self._conn_rfile.read(int(clen)),'utf8')
                if DEBUG:
                    print("CLIENT req.body: %s" % body)
        
        #construct the request object, similar to Flask names
        request = HttpRequest()
        request.method  = method
        request.path    = req.path
        request.args    = params
        request.headers = headers
        request.client_address = self.client_address
        request.body    = body
        return request
        
    def handle_malformed_request_line(self, request_line = ""):
        if DEBUG:
            print("INSIDE HANDLER name='%s' " % 'handle_malformed_request_line')
        print("WARNING: got malformed request_line '%s'" % request_line)

