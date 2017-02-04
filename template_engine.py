try:
    import re
except ImportError:
    import ure as re
    
try:
    from io import StringIO
except ImportError:
    from uio import StringIO
    
DEBUG = False
    
EXPRESSION_TAG_OPEN  = "{{ "
EXPRESSION_TAG_CLOSE = " }}"

RE_TAG = re.compile("{{\s(\w+)\s}}")
    
class Template(object):
    class SyntaxError(Exception):
        pass
        
    def __init__(self, textio):
        self._line_num = 0
        self._textio = textio   #this is file-like
        self._registered_tags = {}
        
    def __iter__(self):
        while True:
            line = self._textio.readline()
            if line == "":
                raise StopIteration
            self._line_num += 1
            #replace tags recursively, at start set remaining line to the whole
            for rep_line in self._replace_tags(line,line):
                yield rep_line

    def format(self, **kwargs):
        self._registered_tags = kwargs
        return self
        
    def _replace_tags(self, line, rline):
        #NOTE this a a generator which yields when a 
        global DEBUG
        if DEBUG:
            print("LINE %d: %r" % (self._line_num, line.strip()))
        start_pos = rline.find(EXPRESSION_TAG_OPEN)
        if start_pos == -1: #no tags found
            yield line
            raise StopIteration
        end_pos = rline.find(EXPRESSION_TAG_CLOSE) + len(EXPRESSION_TAG_CLOSE)
        if end_pos == -1:
            raise SyntaxError("line #%d missing EXPRESSION_TAG_CLOSE '%r'" % (self._line_num,EXPRESSION_TAG_CLOSE))
        tag = rline[start_pos : end_pos]
        if DEBUG:
            print("FOUND TAG: %s" % tag)
        #set up the remainder of the line
        rline = rline[end_pos:]
        m = RE_TAG.match(tag)
        if not m:
            raise SyntaxError("line #%d malformed tag '%s'" % (self._line_num,tag))
        name = m.group(1)
        rep = self._registered_tags.get(name)
        if not rep is None:
            if DEBUG:
                print("REPLACING TAG '%s' -> '%s'" % (name,rep))
            if type(rep) == Template:
                if DEBUG:
                    print("START CHAINING SUBTEMPLATE")
                #we must chain in the sub-template
                part_line = line[:start_pos] #yield what we have so far
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
                line = line.replace(tag, rep)
        else:
            if DEBUG:
                print("UNRECOGNIZED TAG '%s'" % (name,))
        #continue with the remaining line
        if DEBUG:
            print("RLINE: %r" % rline.strip())
        for rep_line in self._replace_tags(line, rline):
            yield rep_line
        
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
    pins_tmp   = Template.from_file("templates/pins.html_template")
    #ptr_tmp    = Template.from_file("templates/pins_table_row.html_template")
    pins_jstmp = Template.from_file("templates/pins.js_template")
    pins_jstmp.format(server_addr = "0.0.0.0")
    pins_tmp.format(table_content = "dummy", comment='', javascript = pins_jstmp)
    with open("doc.html",'w') as rnd:
        for line in pins_tmp:
            rnd.write(line)
################################################################################
# TEST OUTPUT
################################################################################
#    LINE 1: '<!DOCTYPE html>'
#    LINE 2: '<html>'
#    LINE 3: '<head> <title>ESP8266 Pins</title>'
#    LINE 4: '</head>'
#    LINE 5: '<body> <h1>ESP8266 Pins</h1>'
#    LINE 6: '<table border="1"> <tr><th>Pin</th><th>Value</th></tr>{{ table_content }}</table>'
#    FOUND TAG: {{ table_content }}
#    REPLACING TAG 'table_content' -> 'dummy'
#    RLINE: '</table>'
#    LINE 6: '<table border="1"> <tr><th>Pin</th><th>Value</th></tr>dummy</table>'
#    LINE 7: '<div>{{ comment }}</div>'
#    FOUND TAG: {{ comment }}
#    UNRECOGNIZED TAG 'comment'
#    RLINE: '</div>'
#    LINE 7: '<div>{{ comment }}</div>'
#    LINE 8: '</body>'
#    LINE 9: '<script>'
#    LINE 10: '{{ javascript }}'
#    FOUND TAG: {{ javascript }}
#    REPLACING TAG 'javascript' -> '<__main__.Template object at 0x7ff9a4b35780>'
#    START CHAINING SUBTEMPLATE
#    LINE 1: 'document.body.addEventListener("click", function(event) {'
#    LINE 2: 'if (event.target.nodeName == "BUTTON"){'
#    LINE 3: 'var btn_id = event.target.getAttribute("id")'
#    LINE 4: 'console.log("Clicked", btn_id);'
#    LINE 5: 'postToggle(btn_id);'
#    LINE 6: '}'
#    LINE 7: '});'
#    LINE 8: ''
#    LINE 9: 'function postToggle (btn_id) {'
#    LINE 10: "var form = document.createElement('form');"
#    LINE 11: "form.setAttribute('method', 'post');"
#    LINE 12: "form.setAttribute('action', 'http://{{ server_addr }}?btn_id='+btn_id);"
#    FOUND TAG: {{ server_addr }}
#    REPLACING TAG 'server_addr' -> '0.0.0.0'
#    RLINE: "?btn_id='+btn_id);"
#    LINE 12: "form.setAttribute('action', 'http://0.0.0.0?btn_id='+btn_id);"
#    LINE 13: "form.style.display = 'hidden';"
#    LINE 14: 'document.body.appendChild(form)'
#    LINE 15: 'form.submit();'
#    LINE 16: '}'
#    END CHAINING SUBTEMPLATE
#    RLINE: ''
#    LINE 10: ''
#    LINE 11: '</script>'
#    LINE 12: '</html>'


