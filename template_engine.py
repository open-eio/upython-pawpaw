try:
    import re
except ImportError:
    import ure as re
    
try:
    from io import StringIO
except ImportError:
    from uio import StringIO
    
DEBUG = False
    
EXPRESSION_TAG_OPEN  = "{{"
EXPRESSION_TAG_CLOSE = "}}"

RE_EXPRESSION_TAG = re.compile(r"{{\s(\w+)\s}}")

def scan_tag(text, at_pos = 0):
    global DEBUG
    tag_start_pos = text.find(EXPRESSION_TAG_OPEN)
    if tag_start_pos == -1: #no tags found
        return (-1,-1, None)
    at_pos  = tag_start_pos + len(EXPRESSION_TAG_OPEN)
    tag_end_pos = text.find(EXPRESSION_TAG_CLOSE, at_pos) + len(EXPRESSION_TAG_CLOSE)
    if tag_end_pos == -1:
        raise SyntaxError("@pos = %d: missing EXPRESSION_TAG_CLOSE '%r'" % (at_pos,EXPRESSION_TAG_CLOSE))
    tag = text[tag_start_pos : tag_end_pos]
    at_pos = tag_end_pos
    if DEBUG:
        print("@pos = %d: FOUND TAG: %s" % (at_pos,tag))
    m = RE_EXPRESSION_TAG.match(tag)
    if not m:
        raise SyntaxError("@pos = %d: malformed tag '%s' needs to match '%r'" % (at_pos,tag, RE_EXPRESSION_TAG))
    name = m.group(1)
    return (tag_start_pos, tag_end_pos, name)

class BaseTemplate(object):
    def __init__(self, tags = None):
        if tags is None:
            tags = {}
        self._registered_tags = tags
        
    def __str__(self):
        return self.render()
        
    def format(self, **kwargs):
        self._registered_tags = kwargs
        return self
        
    def render(self):
        raise NotImplementedError
        
#class Template(BaseTemplate):
#    def __init__(self, text, tags = None):
        
    
class LazyTemplate(BaseTemplate):
    """  A templating engine that allows chained lazy evaluation of 
         nested subtemplates.
    """
    # `__iter__` is a generator which evaluates 
    # `_replace_tags` which is itself a recursive generator thats scans 
    # each line replacing tags.  If a tag is encountered, then either the 
    # replacement is a string or it is a subtemplate.  If it is a string we 
    # just use the str.replace method.  For the subtemplate case we have to 
    # break the line, yield it, and stitch in all the lines that the 
    # subtemplate generates.  Finally we have to continue with the rest of 
    # the line occuring after the tag.  The upshot of all this crazyness is 
    # a very low RAM footprint since the whole document never needs to be in
    # memory.
    class SyntaxError(Exception):
        pass
        
    def __init__(self, textio, tags = None):
        BaseTemplate.__init__(self, tags)
        self._line_num = 0
        self._textio = textio   #this is file-like
        
    def __del__(self):
        self.close()
        
    def __iter__(self):
        while True:
            line = self._textio.readline()
            if line == "":
                self.close()
                raise StopIteration
            self._line_num += 1
            #replace tags recursively, at start set remaining line to the whole
            for rep_line in self._replace_tags(line,line):
                yield rep_line
    
    def __str__(self):
        return repr(self)
        
    def render(self):
        lines = list(self)
        self.close()
        return "".join(lines)
        
    def _replace_tags(self, line, rline):
        #NOTE this a a generator which yields when a 
        global DEBUG
        if DEBUG:
            print("LINE %d: %r" % (self._line_num, line))
        tag_start_pos, tag_end_pos, tag_name = scan_tag(rline)
        if tag_start_pos == -1: #no tags found
            yield line
            raise StopIteration
        #set up the remainder of the line
        rline = rline[tag_end_pos:]
        rep = self._registered_tags.get(tag_name)
        if not rep is None:
            if DEBUG:
                print("REPLACING TAG '%s' -> '%s'" % (tag_name,rep))
            if issubclass(type(rep),BaseTemplate):
                if DEBUG:
                    print("START CHAINING SUBTEMPLATE")
                #we must chain in the sub-template
                part_line = line[:tag_start_pos] #yield what we have so far
                yield part_line
                #extract all the lines of the sub-template
                for sub_line in rep:
                    yield sub_line
                #reduce the line to the remaining portion
                line = rline
                if DEBUG:
                    print("END CHAINING SUBTEMPLATE")
            else:
                #just a simple string replacement
                line = "".join((line[:tag_start_pos],rep,line[tag_end_pos]))
        else:
            if DEBUG:
                print("UNRECOGNIZED TAG '%s'" % (tag_name,))
        #continue with the remaining line
        if DEBUG:
            print("RLINE: %r" % rline.strip())
        for rep_line in self._replace_tags(line, rline):
            yield rep_line
    
    def close(self):
        self._textio.close()
        
    @classmethod
    def from_file(cls, filename):
        return cls(textio = open(filename,'r'))
        
    @classmethod
    def from_text(cls, text):
        return cls(textio = StringIO(text))
        
################################################################################
# TEST CODE
################################################################################
if __name__ == "__main__":
    DEBUG = True
    #test a well-formed but incomplete template
    pins_tmp   = LazyTemplate.from_file("templates/pins.html_template")
    ptr_tmp    = LazyTemplate.from_file("templates/pins_table_row.html_template")
    try:
        from collections import OrderedDict
    except ImportError: 
        from ucollections import OrderedDict #micrpython specific
    import mock_machine as machine
    PIN_NUMBERS = (0, 2, 4, 5, 12, 13, 14, 15)
    PINS = OrderedDict((i,machine.Pin(i, machine.Pin.IN)) for i in PIN_NUMBERS)
    #pin = PINS[0]
    #row = ptr_tmp.format(pin_id = str(pin), pin_value='HIGH' if pin.value() else 'LOW')
    #row_str = row.render()
    #print("ROW: %r" % row_str)
    table_content = ""
#    table_content = [ptr_tmp.format(pin_id = str(pin),
#                                    pin_value = 'HIGH' if pin.value() else 'LOW',
#                                   ).render() for pn,pin in PINS.items()]
    #table_content = "".join(table_content)
    print("TABLE_CONTENT: %r" % table_content)
    pins_jstmp = LazyTemplate.from_file("templates/pins.js_template")
    pins_jstmp.format(server_addr = "0.0.0.0")
    pins_tmp.format(table_content = table_content, comment='', javascript = pins_jstmp)
    print(repr(pins_tmp.render()))
#    with open("doc.html",'w') as rnd:
#        for line in pins_tmp:
#            rnd.write(line)
################################################################################
# TEST OUTPUT
################################################################################
#    TABLE_CONTENT: ''
#    LINE 1: '<!DOCTYPE html>\n'
#    LINE 2: '<html>\n'
#    LINE 3: '    <head> <title>ESP8266 Pins</title>\n'
#    LINE 4: '    </head>\n'
#    LINE 5: '    <body> <h1>ESP8266 Pins</h1>\n'
#    LINE 6: '        <table border="1"> <tr><th>Pin</th><th>Value</th></tr>{{ table_content }}</table>\n'
#    @pos = 81: FOUND TAG: {{ table_content }}
#    REPLACING TAG 'table_content' -> ''
#    RLINE: '</table>'
#    LINE 6: '        <table border="1"> <tr><th>Pin</th><th>Value</th></tr><'
#    LINE 7: '        <div>{{ comment }}</div>\n'
#    @pos = 26: FOUND TAG: {{ comment }}
#    REPLACING TAG 'comment' -> ''
#    RLINE: '</div>'
#    LINE 7: '        <div><'
#    LINE 8: '    </body>\n'
#    LINE 9: '    <script>\n'
#    LINE 10: '        {{ javascript }}\n'
#    @pos = 24: FOUND TAG: {{ javascript }}
#    REPLACING TAG 'javascript' -> '<__main__.LazyTemplate object at 0x7f61881e5198>'
#    START CHAINING SUBTEMPLATE
#    LINE 1: 'document.body.addEventListener("click", function(event) {\n'
#    LINE 2: '  if (event.target.nodeName == "BUTTON"){\n'
#    LINE 3: '    var btn_id = event.target.getAttribute("id")\n'
#    LINE 4: '    console.log("Clicked", btn_id);\n'
#    LINE 5: '    postToggle(btn_id);\n'
#    LINE 6: '  }\n'
#    LINE 7: '});\n'
#    LINE 8: '  \n'
#    LINE 9: 'function postToggle (btn_id) {\n'
#    LINE 10: "  var form = document.createElement('form');\n"
#    LINE 11: "  form.setAttribute('method', 'post');\n"
#    LINE 12: "  form.setAttribute('action', 'http://{{ server_addr }}?btn_id='+btn_id);\n"
#    @pos = 55: FOUND TAG: {{ server_addr }}
#    REPLACING TAG 'server_addr' -> '0.0.0.0'
#    RLINE: "?btn_id='+btn_id);"
#    LINE 12: "  form.setAttribute('action', 'http://0.0.0.0?"
#    LINE 13: "  form.style.display = 'hidden';\n"
#    LINE 14: '  document.body.appendChild(form)\n'
#    LINE 15: '  form.submit();\n'
#    LINE 16: '}\n'
#    END CHAINING SUBTEMPLATE
#    RLINE: ''
#    LINE 10: '\n'
#    LINE 11: '    </script>\n'
#    LINE 12: '</html>\n'
#    '<!DOCTYPE html>\n<html>\n    <head> <title>ESP8266 Pins</title>\n    </head>\n    <body> <h1>ESP8266 Pins</h1>\n        <table border="1"> <tr><th>Pin</th><th>Value</th></tr><        <div><    </body>\n    <script>\n        document.body.addEventListener("click", function(event) {\n  if (event.target.nodeName == "BUTTON"){\n    var btn_id = event.target.getAttribute("id")\n    console.log("Clicked", btn_id);\n    postToggle(btn_id);\n  }\n});\n  \nfunction postToggle (btn_id) {\n  var form = document.createElement(\'form\');\n  form.setAttribute(\'method\', \'post\');\n  form.setAttribute(\'action\', \'http://0.0.0.0?  form.style.display = \'hidden\';\n  document.body.appendChild(form)\n  form.submit();\n}\n\n    </script>\n</html>\n'

