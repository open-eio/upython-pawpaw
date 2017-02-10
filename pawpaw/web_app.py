import time
try:
    from collections import OrderedDict
except ImportError: 
    from ucollections import OrderedDict #micrpython specific

from .http_server     import HttpServer
from .template_engine import Template, LazyTemplate

DEBUG = True
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
    if DEBUG:
        print("@Router: wrapping class '%s'" % cls)
    
    class RouterWrapped(cls):
        #update the private class to contain all currently registered routes
        _unbound_handler_registry = route.registered_routes.copy()
        def __init__(self,*args,**kwargs):
            handler_registry = kwargs.get("handler_registry")
            if handler_registry is None:
                handler_registry = OrderedDict()
            def bind_method(m):
                return (lambda *args, **kwargs: m(self,*args,**kwargs))
            #bind self to all of the route handlers
            for key, unbound_handler in type(self)._unbound_handler_registry.items():
                handler_registry[key] = handler = bind_method(unbound_handler)
                if DEBUG:
                    print("@Router BOUND HANDLER key='%s': %s" % (key,handler))
            #bind the default handler
            handler_registry['DEFAULT'] = bind_method(type(self).handle_default)
            kwargs['handler_registry'] = handler_registry
            cls.__init__(self,*args, **kwargs)
    
    #remove the registered_routes from the route decorator class 
    #attribute space, this allows for independent routing WebApp instances
    route.registered_routes = OrderedDict()
    return RouterWrapped

################################################################################
# Classes
#-------------------------------------------------------------------------------
class WebApp(object):
    def __init__(self, server_addr, server_port, handler_registry):
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
        addr = (self.server_addr, self.server_port)
        self._server = HttpServer(addr,app=self)
        
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
        tmp = LazyTemplate.from_file("html/404.html")
        context.render_template(tmp)

################################################################################
# TEST  CODE
################################################################################
#if __name__ == "__main__":
#    try:
#        from collections import OrderedDict
#    except ImportError: 
#        from ucollections import OrderedDict #micropython specific
#    
#    import mock_machine as machine
#    
#    SERVER_IP   = '0.0.0.0'
#    SERVER_PORT = 9999
#    PIN_NUMBERS = (0, 2, 4, 5, 12, 13, 14, 15)
#    PINS = OrderedDict((i,machine.Pin(i, machine.Pin.IN)) for i in PIN_NUMBERS)
#    
#    #---------------------------------------------------------------------------
#    @Router
#    class PinServer(PawpawApp):
#        @route("/", methods=['GET','POST'])
#        def pins(self, context):
#            if DEBUG:
#                print("INSIDE ROUTE HANDLER name='%s' " % ('pins'))
#            
#    
#            #open the template files
#            pins_tmp   = LazyTemplate.from_file("templates/pins.html_template")
#            ptr_tmp    =     Template.from_file("templates/pins_table_row.html_template")
#            pins_jstmp = LazyTemplate.from_file("templates/pins.js_template")
#            comment = ""
#           
#            if context.request.method == 'POST':
#                if DEBUG:
#                    print("HANDLING POST REQUEST: args = %r" % context.request.args)
#                #get the button id from the params and pull out the corresponding pin object
#                btn_id = context.request.args['btn_id']
#                pin_id = int(btn_id[3:])#pattern is "btn\d\d"
#                pin = PINS[pin_id]
#                pin.value = not pin.value() #invert the pin state
#                comment = "Toggled pin %d" % pin_id
#                
#            #we make table content a generator that produces one row per iteration
#            def gen_table_content(pins):
#                for pin_num, pin in pins.items():
#                    ptr_tmp.format(pin_id = str(pin),
#                                   pin_value = 'HIGH' if pin.value() else 'LOW',
#                                  )
#                    for line in ptr_tmp.render():
#                        yield line
#            server_base_url = "%s:%s" % (self.server_addr,self.server_port)
#            pins_jstmp.format(server_base_url = server_base_url)
#            pins_tmp.format(table_content = gen_table_content(PINS),
#                            comment=comment,
#                            javascript = pins_jstmp)
#            #finally render the view
#            context.render_template(pins_tmp)
#    #---------------------------------------------------------------------------
#    # Create application instance binding to localhost on port 9999
#    app = PinServer(server_addr = '0.0.0.0',
#                    server_port = 9999,
#                   )

#    # Activate the server; this will keep running until you
#    # interrupt the program with Ctrl-C
#    app.serve_forever()
