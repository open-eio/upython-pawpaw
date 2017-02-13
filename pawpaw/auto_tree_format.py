try:
    import json
except ImportError:
    import ujson as json #micropython specific
    
from . import urllib_parse

class AutoTreeFormat(object):
    def __init__(self, tree):
        self._tree = tree
        
    def gen_yaml(self, indent_step=2):
        buff = []
        self._indent = ""
        def inode_func(k, sn):
            if hasattr(sn,"items"):
                buff.append("%s%s:\n" % (self._indent,k))
                self._indent += " "*indent_step  #indent to next level
            else:
                buff.append("%s%s: " % (self._indent,k))
            return (k,sn)
        def anode_func(k, sn):
            if hasattr(sn,"items"):
                self._indent = self._indent[:-indent_step] #dedent
            return
        def lnode_func(ln):
            buff.append("%r\n" % (ln,))
            return (ln,)
            
        for node in self._recur_walk(inner_node_func = inode_func,
                                     after_node_func = anode_func,
                                     leaf_node_func  = lnode_func,
                                    ):
            #buff is updated through side-effects in the node functions
            yield "".join(buff)
            buff = []
        
    def gen_html_form(self, indent_step=2):
        buff = []
        self._indent = ""
        self._node_path = []
        def inode_func(k, sn):
            if hasattr(sn,"items"):
                buff.append("%s<li>%s:\n" % (self._indent,k))
                self._indent += " "*indent_step  #indent to next level
                buff.append("%s<ul>\n" % (self._indent,))
                self._indent += " "*indent_step  #indent to next level
                self._node_path.append(k)
            else:
                self._node_path.append(k)
                name = ".".join(self._node_path)
                buff.append('%s<div class="slot"><label>%s:</label><input type="text" name="%s" ' % (self._indent,k,name))
                self._node_path.pop()
            return (k,sn)
        def anode_func(k, sn):
            if hasattr(sn,"items"):
                self._indent = self._indent[:-indent_step] #dedent
                buff.append("%s</ul>\n" % (self._indent,))
                self._indent = self._indent[:-indent_step] #dedent
                buff.append("%s</li>\n" % (self._indent,))
                self._node_path.pop()
            return
        def lnode_func(ln):
            buff.append('value="%s"></div>\n' % (ln,))
            return (ln,)

        for node in self._recur_walk(inner_node_func = inode_func,
                                     after_node_func = anode_func,
                                     leaf_node_func  = lnode_func,
                                    ):
            #buff is updated through side-effects in the node functions
            yield "".join(buff)
            buff = []
        
    def _recur_walk(self,
                    node = None,
                    inner_node_func = lambda k,sn: (k,sn),
                    after_node_func = lambda k,sn: (),
                    leaf_node_func  = lambda ln: (ln,),
                    ):
        if node is None:
            node = self._tree
        if hasattr(node,"items"):
            for key, subnode in node.items():
                #this is a inner node, wrap in a 2-tuple
                yield inner_node_func(key,subnode)
                #recur over sub-nodes
                gen_nodes = self._recur_walk(node=subnode,
                                             inner_node_func=inner_node_func,
                                             leaf_node_func=leaf_node_func,
                                            )
                for n in gen_nodes:
                    yield n
                after_node_func(key, subnode)
        else: #is a leaf node
            #wrap in a 1-tuple
            yield leaf_node_func(node)
    
    @classmethod
    def from_json_file(cls, filename):
        f = open(filename,'r')
        d = json.loads(f.read())
        return cls(tree=d)
        
def parse_form_url(urlencoded_form):
    form_items = urllib_parse.parse_qsl(urlencoded_form)
    d = {}
    for path, value in form_items:
        p = d
        names = path.split(".")
        for name in names[:-1]:
            c = p.get(name,{})
            p[name] = c
            p = c
        try:
            #convert string into a python type, safely
            value = eval(value,{"__builtins__":None},{})
        except NameError:
            pass
        except TypeError:
            pass
        #otherwise keep as string
        p[names[-1]] = value
    return d
    
################################################################################
# TEST CODE
################################################################################
#if __name__ == "__main__":
#    ATF = AutoTreeFormat.from_json_file("SECRET_CONFIG.json")
#    from pawpaw import LazyTemplate
#    tmp = LazyTemplate.from_file("html/config_form.html", endline = "", rstrip_lines = False)
#    gen_form = ATF.gen_html_form()
#    tmp.format(form_content = gen_form)
#    with open("form.html",'w') as f:
#        for chunk in tmp:
#            print("writing chunk: %r" % chunk)
#            f.write(chunk)
#    
