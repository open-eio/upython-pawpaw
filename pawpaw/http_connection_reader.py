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

DEBUG = False
DEBUG = True
################################################################################
# Classes
class HttpRequest(object):
    __slots__ = 'method','path','args','headers','client_address'

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
            method, req, protocol = request_line.split()
        except ValueError:
            self.handle_malformed_request_line(request_line)
            return None
        #split off any params if they exist
        req = req.split("?")
        req_path = req[0]
        params = {}
        if len(req) == 2:
            items = req[1].split("&")
            for item in items:
                item = item.split("=")
                if len(item) == 1:
                    params[item[0]] = None
                elif len(item) == 2:
                    params[item[0]] = item[1]
        #read the remaining request headers
        headers = OrderedDict()
        while True:
            line = str(self._conn_rfile.readline(),'utf8').strip()
            if DEBUG:
                print("CLIENT: %r" % line)
            if not line or line == '\r\n':
                break
            key, val = line.split(':',1)
            headers[key] = val
        #construct the request object, similar to Flask names
        request = HttpRequest()
        request.method  = method
        request.path    = req_path
        request.args    = params
        request.headers = headers
        request.client_address = self.client_address
        return request
        
    def handle_malformed_request_line(self, request_line = ""):
        if DEBUG:
            print("INSIDE HANDLER name='%s' " % 'handle_malformed_request_line')
        print("WARNING: got malformed request_line '%s'" % request_line)

