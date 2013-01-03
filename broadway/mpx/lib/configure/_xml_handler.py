"""
Copyright (C) 2001 2002 2003 2004 2006 2010 2011 Cisco Systems

This program is free software; you can redistribute it and/or         
modify it under the terms of the GNU General Public License         
as published by the Free Software Foundation; either version 2         
of the License, or (at your option) any later version.         
    
This program is distributed in the hope that it will be useful,         
but WITHOUT ANY WARRANTY; without even the implied warranty of         
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         
GNU General Public License for more details.         
    
You should have received a copy of the GNU General Public License         
along with this program; if not, write to:         
The Free Software Foundation, Inc.         
59 Temple Place - Suite 330         
Boston, MA  02111-1307, USA.         
    
As a special exception, if other files instantiate classes, templates  
or use macros or inline functions from this project, or you compile         
this file and link it with other works to produce a work based         
on this file, this file does not by itself cause the resulting         
work to be covered by the GNU General Public License. However         
the source code for this file must still be made available in         
accordance with section (3) of the GNU General Public License.         
    
This exception does not invalidate any other reasons why a work         
based on this file might be covered by the GNU General Public         
License.
"""
from xml import sax 
import _configuration
from _tree import Tree_Builder, Iterator
import types
import string
from mpx.lib import msglog

def current_state(node):
    return 'RUNNING'

##
# Document Handler for parsing mpx configuration xml documents.
# 
class docHandler(sax.ContentHandler):
    def __init__(self,format=0):
        sax.ContentHandler.__init__(self)
        self.format = format
        self.current_ion = None
        self.tree_builder = Tree_Builder()
        self.dict_stack = []
        self.list_stack = []
        self.property_stack = []
        self.tag_stack = []
        self.current_depth = 0
        self.current_dict = None
        self.current_list = None
        self.current_property = None 
    ##
    # Called by xml_parser when document starts.
    #
    def startDocument(self):
        pass

    ##
    # Called by xml_parser when document ends.
    #
    def endDocument(self):
        pass

    ##
    # Called by xml_parser when an opening tag is encountered.
    #
    # @param name  Name of the tag opened.
    #
    # @param attrs  <code>xml attr</code> object containing
    #               attributes enclosed in opening tag.
    #
    def startElement(self, name, attrs):
        xml = ''
        if type(attrs) != types.DictType:
            attrs = attrs._attrs
        if self.format:
            xml = '\t' * self.current_depth
        xmls = []
        xmls.append('<')
        if name == 'property':
            xmls.append(self.property_start(attrs))
            self.tag_stack.append(name)
        elif name == 'node':
            xmls.append(self.node_start(attrs))
            self.tag_stack.append(name)
        elif name == 'dictionary':
            xmls.append(self.dictionary_start(attrs))
            self.tag_stack.append(name)
        elif name == 'list':
            xmls.append(self.list_start(attrs))
            self.tag_stack.append(name)
        elif hasattr(self, name + '_start'):
            xmls.append(eval('self.' + name + '_start(attrs)'))
            self.tag_stack.append(name)
        self.current_depth += 1
        xmls.append('>')
        if self.format:
            xmls.append('\n')
        return xml.join(xmls)

    ##
    # Called by xml_parser when a closing tag is encountered.
    #
    # @param name  Name of the tag closed.
    #
    def endElement(self, name):
        self.current_depth -= 1
        xml = '\t' * self.current_depth
        xmls =[]
        xmls.append('</')
        if name == 'property':
            self.tag_stack.pop()
            xmls.append(self.property_end())
        elif name == 'node':
            self.tag_stack.pop()
            xmls.append(self.node_end())
        elif name == 'dictionary':
            self.tag_stack.pop()
            xmls.append(self.dictionary_end())
        elif name == 'list':
            self.tag_stack.pop()
            xmls.append(self.list_end())
        elif hasattr(self, name + '_end'):
            self.tag_stack.pop()
            xmls.append(eval('self.' + name + '_end()'))
        xmls.append('>\n')
        return xml.join(xmls) 

    ##
    # Called by <code>startElement</code> func when a node tag is opened.
    #
    # @param attrs  Attributes in node tag.
    #
    def node_start(self, attrs):
        # makes a copy of the dictionary in attrs, this will get all entries
        #   put in the <node> tag itself
        self.current_dict = _copy_dict(attrs)
        self.current_config = _configuration.Configuration()
        self.current_config._set_config(self.current_dict)
        self.tree_builder.open_node(self.current_config)
        xml = 'node'
        xmls = [' %s=\'%s\'' % (key, self.current_dict[key]) for key in self.current_dict.keys()]
        #for key in self.current_dict.keys():
        #    xml += ' ' + key + '=\'' + self.current_dict[key] + '\''
        return xml.join(xmls)

    ##
    # Called by <code>endElement</code> func when a node tag is closed.
    #    
    def node_end(self):
        self.tree_builder.close_node(self.current_config)
        self.current_dict = None
        return 'node'

    ##
    # Called by <code>startElement</code> func when a config tag is opened.
    #
    # @param attrs  Attributes in config tag.
    #    
    def config_start(self, attrs):
        # don't need to do anything because attribs was
        #   started in node_start
        return 'config'
    
    ##
    # Called by <code>endElement</code> func when a config tag is closed.
    #   
    def config_end(self):
        self.current_config._set_config(self.current_dict)
        self.current_dict = None
        return 'config'

    ##
    # Called by <code>startElement</code> func when a property tag is opened.
    #
    # @param attrs  Attributes in property tag.
    #      
    def property_start(self, attrs):
        if self.current_property != None:
            self.property_stack.append(self.current_property)
        self.current_property = {}
        xml = 'property'
        xmls = []
        self.current_property['key'] = None
        if attrs.has_key('name'):
            # has name, must be a dictionary entry
            self.current_property['key'] = str(attrs['name'])
            xmls.append('property name=\'%s\'' % (self.current_property['key'],))
        
        self.current_property['value'] = None
        if attrs.has_key('value'):
            self.current_property['value'] = str(attrs['value'])
            xmls.append(' value=\'%s\'' % (self.current_property['value'],))
        return xml.join(xmls)
    
    ##
    # Called by <code>startElement</code> func when a property tag is closed.
    # 
    def property_end(self):
        if self.current_property['key'] == None:
            # key is None, the current_prop is a value for a list
            self.current_list.append(self.current_property['value'])
        else:
            # the property must be a dictionary entry for the current_dict
            self.current_dict[self.current_property['key']] = self.current_property['value']
        
        if len(self.property_stack) > 0:
            self.current_property = self.property_stack.pop()
        else:
            self.current_property = None
        return 'property'
    
    ##
    # Called by <code>startElement</code> func when a list tag is opened.
    #
    # @param attrs  Attributes in list tag.
    #   
    def list_start(self, attrs):
        # to make a list a value inside a parent list, an empty property tag
        #   must be inserted, then that property's value will be set to this
        #   list
        if self.current_list != None:
            # new list is an entry in the current list, push the current
            self.list_stack.append(self.current_list)
        self.current_list = []
        return 'list'

    ##
    # Called by <code>startElement</code> func when a list tag is closed.
    # 
    def list_end(self):
        self.current_property['value'] = self.current_list
        if len(self.list_stack) > 0:
            # current list is a member of another list, pop the parent
            self.current_list = self.list_stack.pop()
        else:
            self.current_list = None
        return 'list'

    ##
    # Called by <code>startElement</code> func when a dictionary tag is opened.
    #
    # @param attrs  Attributes in dictionary tag.
    #    
    def dictionary_start(self, attrs):
        # dictionary tags are only found in config tags,
        #   since config tags create dictionaries also
        #   dictionary tags are always members of config dictionaries
        self.dict_stack.append(self.current_dict)
        self.current_dict = {}
        return 'dictionary'
    
    ##
    # Called by <code>startElement</code> func when a dictionary tag is closed.
    # 
    def dictionary_end(self):
        if self._parent_tag() == 'list':
            # this dictionary is a member of a list, append it to that list
            self.current_list.append(self.current_dict)
        else:
            # this dicionary is the value of the current_property
            self.current_property['value'] = self.current_dict
        self.current_dict = self.dict_stack.pop()
        return 'dictionary'

    def _parent_tag(self):
        # allows a given tag to see what tag it is embedded in.
        #   Needed for dictionaries to see if they should set
        #   the current_value or append themselves to a list
        return self.tag_stack[len(self.tag_stack) - 1]
    
    ##
    # Get the root Element of the the parsed Document.
    #
    # @return root of <code>tree_builder</code> object.
    #
    def get_root(self):
        return self.tree_builder.get_root()


##
# @return The root <code>Configuration</code> object from the XML
#         configuration file named <code>fileName</code>.
#
def parse_xml(fileName):
    parser = sax.make_parser()
    dh = docHandler()
    parser.setContentHandler(dh)
    parser.parse(fileName)
    return dh.get_root()

##
# Get xml representation from running framework.
#
# @param root  String or node representing the root
#              of the xml tree you want.
# @return String containing xml.
# @todo handle dictionary and list type values correctly.
#
def build_xml(root, encode=1, get_state=0):
    from mpx.lib.node import as_node,as_internal_node
    if type(root) == types.StringType:
        root = as_internal_node(root)
    it = Iterator(root, 0)
    node_stack = []
    dh = docHandler()
    xml = ''
    while it.has_more():
        node = it.get_next_node()
        while (len(node_stack) and 
               node_stack[len(node_stack) - 1] is not node.parent):
            xml += dh.endElement('node')
            node_stack.pop()
        node_stack.append(node)
        config = node.configuration()
        
        state = current_state(node)
        xml += dh.startElement('node', {'name':config['name'], 'state':state})
        xml += dh.startElement('config', {})
        for property in config.keys():
            if property == 'name':
                continue
            value = config[property]
            if encode:            
                if type(value) != types.StringType:             
                    value = str(value)
                value = _encode_xml(value)
                
            xml += dh.startElement('property', {'name' : property, 'value' : value})
            xml += dh.endElement('property')
        xml += dh.endElement('config')

    while len(node_stack) > 0:
        xml += dh.endElement('node')
        node_stack.pop()
    return xml

def save_xml(root, encode=1, get_state=0):
    from mpx.lib.node import as_node,as_internal_node
    if type(root) == types.StringType:
        root = as_internal_node(root)
    it = Iterator(root, 0)
    node_stack = []
    dh = docHandler()
    f = file('/var/mpx/config/allyway.xml','w')
    while it.has_more():
        xml = ''
        node = it.get_next_node()
        while (len(node_stack) and 
               node_stack[len(node_stack) - 1] is not node.parent):
            xml += dh.endElement('node')
            node_stack.pop()
        node_stack.append(node)
        config = node.configuration()
        
        state = current_state(node)
        xml += dh.startElement('node', {'name':config['name'], 'state':state})
        xml += dh.startElement('config', {})
        for property in config.keys():
            if property == 'name':
                continue
            value = config[property]
            if encode:            
                if type(value) != types.StringType:             
                    value = str(value)
                value = _encode_xml(value)
                
            xml += dh.startElement('property', {'name' : property, 'value' : value})
            xml += dh.endElement('property')
        xml += dh.endElement('config')
        #write this xml segment to the file
        f.write(xml)
        

    while len(node_stack) > 0:
        f.write(dh.endElement('node'))
        node_stack.pop()
    f.close()
    return

def interrogate_nodes(root, get_state=1):
    from mpx.lib.node import as_node,as_internal_node
    #print 'enter interrogate_node'
    if type(root) == types.StringType:
        root = as_internal_node(root)
    it = Iterator(root, 0)
    node_stack = []
    node_interrogation = []
    #COUNTER = 0
    while it.has_more():
        node = it.get_next_node()
        #while (len(node_stack) and node_stack[len(node_stack) - 1] is not node.parent):
            #node_stack.pop()
        #node_stack.append(node)
        
        config = None
        state=''
        try:
            config = node.configuration()
            for k in config.keys():
                value = config[k]
                if type(value) == types.StringType:             
                    config[k] = _encode_xml(value)
            state = current_state(node)
        except Exception, e:
            config = {}
            config['__state__'] = 'Error'
            ## Should report error?

        config['__state__'] = str(state)
        
        node_interrogation.append(config)

        #COUNTER += 1
        #print str(COUNTER)
        #try:
            #print node.name
        #except:
            #pass
        
    #print 'almost done with build_xml'
    #while len(node_stack) > 0:
        #node_stack.pop()
    #print 'done with build_xml'
    return node_interrogation

## Encode the xml if needed to make valid
def _encode_xml(value):
    value = value.replace('&','&amp;')
    value = value.replace('<','&lt;')
    value = value.replace('>','&gt;')
    value = value.replace('"', '&quot;')
    value = value.replace("'", '&apos;')
    answer = ''
    for c in value:
        if c not in string.printable:
            answer += ('&#' + str(ord(c)) + ';')
        else:
            answer += c
    return answer

##
# Get a copy of a dictionary, making each key and value
# a standard string...eliminating uu encoding, in the proccess
#
# @param dict  Dictionary to copy.
#
# @return Copy of <code>dict</code> passed in.
#
def _copy_dict(dict):
    copy = {}
    for key in dict.keys():
        copy[str(key)] = str(dict[key])
    return copy

