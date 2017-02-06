import time, socket

try:
    from collections import OrderedDict
except ImportError: 
    from ucollections import OrderedDict #micrpython specific

from socketserver import TCPServer, StreamRequestHandler

DEBUG = True

SERVER_IP   = '0.0.0.0'
SERVER_PORT = 9999

class HTTPHandler(StreamRequestHandler):
    headers_template = [
        "HTTP/1.1 200 OK",
        "Content-Length: {content_length}",  #hold this place with a formatter
        "Content-Type: text/html",
        "Connection: close",
        ""  #NOTE blank line needed!
    ]

    headers_template = "\r\n".join(headers_template)
    handler_registry = OrderedDict()
    
    def setup(self):
        StreamRequestHandler.setup(self)
    
    def handle(self):
        global DEBUG
        # self.rfile is a file-like object created by the handler;
        # we can now use e.g. readline() instead of raw recv() calls
        #parse the request header
        header_line = str(self.rfile.readline(),'utf8').strip()
        if DEBUG:
            print("CLIENT: %s" % header_line)
        method, req, protocol = header_line.split()
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
        while True:
            line = str(self.rfile.readline(),'utf8').strip()
            if DEBUG:
                print("CLIENT: %r" % line)
            if not line or line == b'\r\n':
                break
        # Likewise, self.wfile is a file-like object used to write back
        # to the client
        #buff = []
        #buff.append("%s %s %r" % (method,req_path,params))
        #self.wfile.write(bytes("".join(buff),'utf8'))


# Create the server, binding to localhost on port 9999
server = TCPServer((SERVER_IP, SERVER_PORT), HTTPHandler)

# Activate the server; this will keep running until you
# interrupt the program with Ctrl-C
server.serve_forever()
