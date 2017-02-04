try:
    import re
except ImportError:
    import ure as re
    
DEBUG = True
    
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
        return self
        
    def __next__(self):
        line = self._textio.readline()
        if line == "":
            raise StopIteration
        self._line_num += 1
        #replace tags recursively, at start set remaining line to the whole
        return self._replace_tags(line,line)
        
    def format(self, **kwargs):
        self._registered_tags = kwargs
        
    def _replace_tags(self, line, rline):
        if DEBUG:
            print("LINE: %r" % line.strip())
            print("RLINE: %r" % rline.strip())
        start_pos = rline.find(EXPRESSION_TAG_OPEN)
        if start_pos == -1: #no tags found
            return line
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
            line = line.replace(tag, rep)
        else:
            if DEBUG:
                print("UNRECOGNIZED TAG '%s'" % (name,))
        #continue with the remaining line
        return self._replace_tags(line, rline)
        
    @classmethod
    def from_file(cls, filename):
        return cls(textio = open(filename,'r'))
        
################################################################################
# TEST CODE
################################################################################
if __name__ == "__main__":
    tmp = Template.from_file("test.html_template")
    tmp.format(table_content = "dummy", comment1="hello1")
    for line in tmp:
        pass
