import time

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
    registered_routes = OrderedDict()

    def __init__(self, path, methods = None):
        #this runs upon decoration
        self.path = path
        if methods is None:
            methods = ["GET"]
        self.req_methods = methods
        
    def __call__(self, m):
        #this runs upon decoration immediately after __init__
        #add the method to the handler_registry with path as key
        for req_method in self.req_methods:
            key = "%s %s" % (req_method, self.path)
            if DEBUG:
                print("@route REGISTERING HANDLER '%s' on method '%s'" % (key,m))
            self.registered_routes[key] = m
        return m

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
        _unbound_handler_registry = route.registered_routes.copy()
        def __init__(self,*args,**kwargs):
            handler_registry = kwargs.get("handler_registry")
            if handler_registry is None:
                handler_registry = OrderedDict()
            def bind_method(m):
                return (lambda *args2, **kwargs2: m(self,*args2,**kwargs2))
            #bind self to all of the route handlers
            for key, unbound_handler in type(self)._unbound_handler_registry.items():
                handler_registry[key] = handler = bind_method(unbound_handler)
                if DEBUG:
                    print("@Router BOUND HANDLER key='%s': %s" % (key,handler))
            #bind the default handler
            handler_registry['DEFAULT'] = bind_method(type(self).handle_default)
            kwargs['handler_registry'] = handler_registry
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
                 handler_registry,
                 log_filename = DEFAULT_LOG_FILENAME,
                 socket_timeout = None,  #default is BLOCKING
                ):
        if DEBUG:
            print("INSIDE WebApp.__init__:")
            print("\tserver_addr: %s" % server_addr)
            print("\tserver_port: %s" % server_port)
            try:
                from micropython import mem_info
                mem_info()
            except ImportError:
                pass
                
        # Create the server, binding to localhost on port 9999
        self.server_addr = server_addr
        self.server_port = server_port
        self.handler_registry = handler_registry
        self.log_filename = log_filename
        addr = (self.server_addr, self.server_port)
        self._server = HttpServer(addr,app=self,timeout=socket_timeout)
        
    def serve_forever(self):
        if DEBUG:
            print("INSIDE WebApp.serve_forever")
            try:
                from micropython import mem_info
                mem_info()
            except ImportError:
                pass
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        self._server.serve_forever()
    
    def handle_default(self, context):
        if DEBUG:
            print("INSIDE HANDLER name='%s' " % ('HttpConnectionResponder.handle_default'))
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

