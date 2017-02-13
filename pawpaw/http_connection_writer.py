import time, socket

try:
    import sys
    from sys import print_exception #micropython specific
except ImportError:
    import traceback
    print_exception = lambda exc: traceback.print_exc()

try:
    from collections import OrderedDict
except ImportError: 
    from ucollections import OrderedDict #micropython specific
    
try:
    import json
except ImportError:
    import ujson as json #micropython specific
    
from .template_engine import Template, LazyTemplate

DEBUG = False
DEBUG = True

MIME_TYPES = {
    "html" : "text/html",
    "jpeg" : "image/jpeg",
    "jpg"  : "image/jpeg",
    "json" : "application/json",
    "txt"  : "text/plain",
    "yaml" : "text/yaml",
}
DEFAULT_MIME_TYPE = 'application/octet-stream'
################################################################################
# Classes

class HttpConnectionWriter(object):
    _newline_bytes = bytes("\r\n", 'utf8')
    
    def __init__(self, conn_wfile, request):
        self._conn_wfile = conn_wfile
        self.request    = request
        
    def send_file(self, filename,
                  status  = "HTTP/1.1 200 OK",
                  headers = None,
                  chunksize = 64):
        if headers is None:
            headers = OrderedDict()
        if not 'Content-Type' in headers.keys():
            #determine MIME types based on extension
            ext = filename.split("/")[-1].split(".")[-1]
            mtype = MIME_TYPES.get(ext,DEFAULT_MIME_TYPE)
            headers['Content-Type'] = mtype
        #wrap the file in a generator
        def gen_tmp():
            with open(filename, 'r') as f:
                while True:
                    chunk = f.read(chunksize)
                    if not chunk:
                        return
                    yield chunk
        tmp = gen_tmp()
        self.render_template(tmp, headers=headers)
        
    def send_json(self, resp):
        tmp = Template(text=json.dumps(resp))
        headers = OrderedDict()
        headers['Content-Type'] = 'application/json'
        self.render_template(tmp, headers = headers)
        
    def render_template(self, tmp,
                        status  = "HTTP/1.1 200 OK",
                        headers = None):
        global DEBUG
        if DEBUG:
            print("INSIDE METHOD name='%s' " % ('HttpConnectionResponder.render_template'))
            try:
                from micropython import mem_info
                mem_info()
            except ImportError:
                pass
        if headers is None:
            headers = OrderedDict()
        headers['Content-Type'] = headers.get('Content-Type', 'text/html')
        # test if we can iterate over tmp to produce output text
        # the follow is a hueristic iterablility test that works for generators
        # and other iterable containers on upython
        tmp_isiterable = False
        try:
            if tmp is iter(tmp):
                if hasattr(tmp,'__next__') or hasattr(tmp,'next'):
                    #tests pass here
                    tmp_isiterable = True
        except TypeError:
            pass
            
        if tmp_isiterable:
            #use chunked transfer coding for an iterable template
            headers['Transfer-Encoding'] = 'chunked'
            #send headers
            self._send_response_headers(status, headers)
            #send in chunks
            self._send_by_chunks(tmp)
        else:
            content = tmp.render().read() #read the StringIO or stream interface
            #compute and send using Content-Length
            headers['Content-Length'] = "%d" % len(content)
            #send headers
            self._send_response_headers(status, headers)
            #send all at once
            self._send(content)
        if DEBUG:
            print("LEAVING METHOD name='%s' " % ('HttpConnectionResponder.render_template'))
            try:
                from micropython import mem_info
                mem_info()
            except ImportError:
                pass
        
    def _send_response_headers(self, status, headers):
        global DEBUG
        if DEBUG:
            print("INSIDE METHOD name='%s' " % ('HttpConnectionResponder.send_response_headers'))
        w  = self._conn_wfile.write
        nl = self._newline_bytes
        w(bytes(status.rstrip(),'utf8'))
        w(nl)
        for key, val in headers.items():
            line = "%s: %s" % (key.strip(),val.strip())
            w(bytes(line,'utf8'))
            w(nl)
        #IMPORTANT final blank line
        w(nl)
        
    def _send(self, content):
        global DEBUG
        if DEBUG:
            print("INSIDE METHOD name='%s' " % ('HttpConnectionResponder.send'))
        self._conn_wfile.write(bytes(content,'utf8'))
        self._flush()
        
    def _send_by_chunks(self, chunk_iter):
        global DEBUG
        if DEBUG:
            print("INSIDE METHOD name='%s'" % ('HttpConnectionResponder.send_by_chunks'))
        w  = self._conn_wfile.write
        nl = self._newline_bytes
        for chunk in chunk_iter:
            chunk_bytes = bytes(chunk,'utf8')
            chunk_len = len(chunk_bytes)     #IMPORTANT, encode before counting!
            w(bytes("%X" % chunk_len,'utf8')) #chunk size specified in hexadecimal
            w(nl)
            w(chunk_bytes)
            w(nl)
        #IMPORTANT chunk trailer
        w(b"0")
        w(nl)
        w(nl)
        self._flush()
        
    def _flush(self):
        # in micropython makefile is a no-op, so wfile is still a 
        # usocket.socket object and thus has no flush method
        try:
            self._conn_wfile.flush()
        except AttributeError:
            #on the first error this method gets replaced with a no-op
            self._flush = lambda: None
################################################################################
# TEST  CODE
################################################################################
