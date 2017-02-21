import time

try:
    import sys
    from sys import print_exception #micropython specific
except ImportError:
    import traceback
    print_exception = lambda exc, file_: traceback.print_exc(file=file_)
    
try:
    import re
except ImportError:
    import ure as re

try:
    from collections import OrderedDict
except ImportError: 
    from ucollections import OrderedDict #micropython specific

try:
    from io import StringIO
except ImportError:
    from uio import StringIO

from .http_server     import HttpServer
from .template_engine import Template, LazyTemplate

DEBUG = True
DEFAULT_LOG_FILENAME = "logs/WebApp.yaml"
LOG_FILESIZE_LIMIT   = 2**20 #1MB
################################################################################
# DECORATORS
#-------------------------------------------------------------------------------
# @route
#a method decorator to automate handling of HTTP route dispatching
class route(object):
    registered_paths  = OrderedDict()
    registered_regexs = OrderedDict()

    def __init__(self, path = None, regex = None, methods = None):
        #this runs upon decoration
        self.path = path
        if not regex is None and not hasattr(regex, "match"):
            regex = re.compile(regex)
        self.regex = regex
        if methods is None:
            methods = ["GET"]
        self.req_methods = methods
        
    def __call__(self, func):
        #this runs upon decoration immediately after __init__
        #add the method to the handler_registry with path as key
        for req_method in self.req_methods:
            #key = "%s %s" % (req_method, self.path)
            if not self.path is None:
                meth_paths = self.registered_paths.get(req_method,OrderedDict())
                meth_paths[self.path] = func
                if DEBUG:
                    print("@route REGISTERING PATH HANDLER in registered_paths['%s']['%s'] as func: %s" % (req_method,self.path,func))
                self.registered_paths[req_method] = meth_paths
        return func

#-------------------------------------------------------------------------------
# @Router
#a class decorator which creates a class-private Routing HttpRequestHandler
def Router(cls):
    log_filename = "logs/{}.yaml".format(cls.__name__)
    if DEBUG:
        print("@Router: wrapping class '%s'" % cls.__name__)
        print("\tLOG FILENAME: %s" % log_filename)
    
    class RouterWrapped(cls):
        #update the private class to contain all currently registered routes
        _unbound_path_handler_registry = route.registered_paths.copy()
        def __init__(self,*args,**kwargs):
            path_handler_registry = kwargs.get("path_handler_registry")
            if path_handler_registry is None:
                path_handler_registry = OrderedDict()
            def bind_method(m):
                return (lambda *args2, **kwargs2: m(self,*args2,**kwargs2))
            #-------------------------------------------------------------------
            # path handlers
            #bind self to all of the route handlers
            uphr = type(self)._unbound_path_handler_registry
            phr  = path_handler_registry
            for req_method in uphr.keys(): #each req_method has a subdict of registered paths
                uphr_rm = uphr[req_method]
                phr_rm  = phr.get(req_method, OrderedDict())
                for path, unbound_path_handler in uphr_rm.items():
                    phr_rm[path] = handler = bind_method(unbound_path_handler)
                    if DEBUG:
                        print("@Router BOUND HANDLER in path_handler_registry['%s']['%s'] as func: %s" % (req_method,path,handler))
                phr[req_method] = phr_rm
            #bind the default handler
            path_handler_registry['DEFAULT'] = bind_method(type(self).handle_default)
            kwargs['path_handler_registry'] = path_handler_registry
            #-------------------------------------------------------------------
            # regex handlers
            
            #-------------------------------------------------------------------
            #setup the log file
            kwargs['log_filename'] = log_filename
            cls.__init__(self,*args, **kwargs)
    
    #remove the registered_routes from the route decorator class 
    #attribute space, this allows for independent routing WebApp instances
    route.registered_routes = OrderedDict()
    return RouterWrapped

################################################################################
# Classes
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Logger - a context manager class for making log entries in YAML format.
#          File size is limited to LOG_FILESIZE_LIMIT over which entries will
#          wrap around to beginning of file.
class Logger(object):
    def __init__(self, filename, app):
        self.filename = filename
        self.app = app
        self.buffer = []
    def __enter__(self):
        self.log_file = open(self.filename,'a')
        self.buffer.append("---\n") #YAML start doc
        try: #get a timestamp
            ts = self.app.get_timestamp()
            self.buffer.append("Time: %s\n" % ts)
        except AttributeError:
            pass
        return self
    def __exit__(self, *args):
        self.buffer.append("...\n") #YAML end doc
        entry = "".join(self.buffer)
        fsz = self.log_file.tell()
        if fsz + len(entry) > LOG_FILESIZE_LIMIT:
            #log file exceeds limit so wrap back to beginning
            self.log_file.seek(0,0)
        self.log_file.write(entry)
        self.log_file.close()
    def write(self, text):
        self.buffer.append(text)
    def write_exception(self, exc):
        #NOTE print_exception has an awkward interface, accepting only a file as
        # its second arg, we fake it out
        sfile = StringIO()
        print_exception(exc, sfile)
        sfile.seek(0,0)
        self.write("Exception: |\n") #this starts a multiline literal block
        for line in sfile:
            self.write("    ") #indent each line of block
            self.write(line)
        #end when dedented
        sfile.close()

#-------------------------------------------------------------------------------
# WebApp - a basic application which responds to HTTP requests over a socket
#          interface.
class WebApp(object):
    def __init__(self,
                 server_addr,
                 server_port,
                 path_handler_registry,
                 log_filename = DEFAULT_LOG_FILENAME,
                 socket_timeout = None,  #default is BLOCKING
                ):
        if DEBUG:
            print("INSIDE WebApp.__init__:")
            print("\tserver_addr: %s" % server_addr)
            print("\tserver_port: %s" % server_port)
            print("\tsocket_timeout: %s" % socket_timeout)
            try:
                from micropython import mem_info
                mem_info()
            except ImportError:
                pass
                
        # Create the server, binding to localhost on port 9999
        self.server_addr = server_addr
        self.server_port = server_port
        self.path_handler_registry = path_handler_registry
        self.log_filename = log_filename
        addr = (self.server_addr, self.server_port)
        self._server = HttpServer(addr,app=self,timeout=socket_timeout)
        
    def serve_forever(self):
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        self._server.serve_forever()
        
    def serve_once(self):
        # For success True will be returned, otherwise (timedout) False
        return self._server.handle_request()
    
    def handle_default(self, context):
        if DEBUG:
            print("INSIDE ROUTE HANDLER 'WebApp.handle_default'")
            print("context.request:\n%s" % context.request)
        context.send_file("html/404.html")
        
    def get_logger(self):
        return Logger(self.log_filename, app = self)
        
    def get_timestamp(self):
        try:
            import machine
            rtc = machine.RTC()
            dt = rtc.datetime()
            year, month, day, weekday, hour, minute, second, millisecond = dt
            timestamp = "{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}".format(
              year=year, month=month, day=day, hour=hour, minute=minute, second=second)
            return timestamp
        except ImportError:
            import datetime
            dt = datetime.datetime.now()
            timestamp = "{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}".format(
              year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute, second=dt.second)
            return timestamp


################################################################################
# TEST  CODE
################################################################################
#if __name__ == "__main__":

