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
    from ucollections import OrderedDict #micrpython specific

DEBUG = False
DEBUG = True
################################################################################
# Classes
class HttpRequest(object):
    __slots__ = 'method','path','args','headers','client_address'

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
        phase = "listening for connection"
        client_sock, client_address = self.socket.accept()
        phase = "accepted connection from '%s'" % (client_address,)
        conn_rfile = client_sock.makefile('rb', self.rbufsize)
        conn_wfile = client_sock.makefile('wb', self.wbufsize)
        try:
            #-------------------------------------------------------------------
            #reading request phase
            #on micropython makefile does nothing returns a usocket.socket obj
            conn_reader = HttpConnectionReader(conn_rfile, client_address)
            phase = 'reading request'
            request = conn_reader.parse_request()
            #-------------------------------------------------------------------
            # handler lookup phase
            phase = 'handler lookup'
            handler = None
            if not request is None:
                key = "%s %s" % (request.method, request.path)
                handler = self.app.handler_registry.get(key)
            if handler is None:
                handler = self.app.handler_registry['DEFAULT']
            #-------------------------------------------------------------------
            # response phase
            conn_responder = HttpConnectionResponder(conn_wfile,request)
            phase = 'handling response'
            handler(conn_responder)
        except Exception as exc:
            print('-'*40, file=sys.stderr)
            print("Exception happened during %s" % phase, file=sys.stderr)
            print_exception(exc,sys.stderr)
            print('-'*40, file=sys.stderr)
        finally:
            conn_rfile.close()
            conn_wfile.close()
            client_sock.close()
            import gc
            gc.collect()

#-------------------------------------------------------------------------------
class HttpConnectionReader(object):
    def __init__(self, conn_rfile, client_address):
        self.conn_rfile = conn_rfile
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
        request_line = str(self.conn_rfile.readline(),'utf8').strip()
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
            line = str(self.conn_rfile.readline(),'utf8').strip()
            if DEBUG:
                print("CLIENT: %r" % line)
            if not line or line == b'\r\n':
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

#-------------------------------------------------------------------------------
class HttpConnectionResponder(object):
    _newline_bytes = bytes("\r\n", 'utf8')
    
    def __init__(self, conn_wfile, request):
        self.conn_wfile = conn_wfile
        self.request    = request
        
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
            tmp.__next__
            tmp is tmp.__iter__()
            #tests pass here
            tmp_isiterable = True
        except AttributeError:
            pass
        if tmp_isiterable:
            #use chunked transfer coding for an iterable template
            headers['Transfer-Encoding'] = 'chunked'
            #send headers
            self.send_response_headers(status, headers)
            #send in chunks
            self.send_by_chunks(tmp)
        else:
            content = tmp.render().read() #read the StringIO or stream interface
            #compute and send using Content-Length
            headers['Content-Length'] = len(content)
            #send headers
            self.send_response_headers(status, headers)
            #send all at once
            self.send(content)
        if DEBUG:
            print("LEAVING METHOD name='%s' " % ('HttpConnectionResponder.render_template'))
            try:
                from micropython import mem_info
                mem_info()
            except ImportError:
                pass
        
    def send_response_headers(self, status, headers):
        global DEBUG
        if DEBUG:
            print("INSIDE METHOD name='%s' " % ('HttpConnectionResponder.send_response_headers'))
        w  = self.conn_wfile.write
        nl = self._newline_bytes
        w(bytes(status.rstrip(),'utf8'))
        w(nl)
        for key, val in headers.items():
            line = "%s: %s" % (key.strip(),val.strip())
            w(bytes(line,'utf8'))
            w(nl)
        #IMPORTANT final blank line
        w(nl)
        
    def send(self, content):
        global DEBUG
        if DEBUG:
            print("INSIDE METHOD name='%s' " % ('HttpConnectionResponder.send'))
        self.conn_wfile.write(bytes(content,'utf8'))
        self._flush()
        
    def send_by_chunks(self, chunk_iter):
        global DEBUG
        if DEBUG:
            print("INSIDE METHOD name='%s'" % ('HttpConnectionResponder.send_by_chunks'))
        w  = self.conn_wfile.write
        nl = self._newline_bytes
        for chunk in chunk_iter:
            w(bytes("%X" % len(chunk),'utf8')) #chunk size specified in hexadecimal
            w(nl)
            w(bytes(chunk,'utf8'))
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
            self.conn_wfile.flush()
        except AttributeError:
            #on the first error this method gets replaced with a no-op
            self._flush = lambda: None
################################################################################
# TEST  CODE
################################################################################
#if __name__ == "__main__":
#    SERVER_IP   = '0.0.0.0'
#    SERVER_PORT = 9999
#    
#    #---------------------------------------------------------------------------
#    class TestPawpawApp(HttpRequestHandler):
#        @route("/")
#        def index(self):
#            if DEBUG:
#                print("INSIDE HANDLER name='%s' " % ('index'))
#            try:
#                from collections import OrderedDict
#            except ImportError: 
#                from ucollections import OrderedDict #micropython specific
#            import mock_machine as machine
#    
#            #test a complete template
#            pins_tmp   = LazyTemplate.from_file("templates/pins.html_template")
#            ptr_tmp    =     Template.from_file("templates/pins_table_row.html_template")
#            pins_jstmp = LazyTemplate.from_file("templates/pins.js_template")
#            
#            PIN_NUMBERS = (0, 2, 4, 5, 12, 13, 14, 15)
#            PINS = OrderedDict((i,machine.Pin(i, machine.Pin.IN)) for i in PIN_NUMBERS)
#            PINS[0].value = True
#            PINS[5].value = True
#            #we make table content a generator that produces one row per iteration
#            def gen_table_content(pins):
#                for pin_num, pin in pins.items():
#                    ptr_tmp.format(pin_id = str(pin),
#                                   pin_value = 'HIGH' if pin.value() else 'LOW',
#                                  )
#                    for line in ptr_tmp.render():
#                        yield line
#            pins_jstmp.format(server_addr = "0.0.0.0")
#            pins_tmp.format(table_content = gen_table_content(PINS),
#                            comment='This is a test page!',
#                            javascript = pins_jstmp)
#            #finally render the view
#            self.render_template(pins_tmp)
#    #---------------------------------------------------------------------------
#    # Create the server, binding to localhost on port 9999
#    server = TCPServer((SERVER_IP, SERVER_PORT), TestPawpawApp)

#    # Activate the server; this will keep running until you
#    # interrupt the program with Ctrl-C
#    server.serve_forever()
