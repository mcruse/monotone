"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
import types
import string

#NAE classid to BACnet object type map
class_obj = {147:0, #AI
             149:1, #AO
             165:2, #AV
             148:3, #BI
             150:4, #BO
             185:8, #Device
             263:17, #schedule
             }
def current_state(node):
    return 'RUNNING'

##
# Document Handler for parsing mpx configuration xml documents.
# 
class docHandler(sax.ContentHandler):
    def __init__(self,format=0):
        sax.ContentHandler.__init__(self)
        self.format = format
        self.objects_dict = {}
        self.current_dict = None
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
        if type(attrs) != types.DictType:
            attrs = attrs._attrs
        if name == 'object':
            self.object_start(attrs)
    ##
    # Called by xml_parser when a closing tag is encountered.
    #
    # @param name  Name of the tag closed.
    #
    def endElement(self, name):
        if name == 'object':
            self.object_end()
    ##
    # Called by <code>startElement</code> func when a node tag is opened.
    #
    # @param attrs  Attributes in node tag.
    #
    def object_start(self, attrs):
        # makes a copy of the dictionary in attrs, this will get all entries
        #   put in the <node> tag itself
        self.current_dict = _copy_dict(attrs)
        try:
            #was object id filtered before.  Changed from using external object id list to class id filter
            if int(self.current_dict['classid']) in class_obj.keys(): #self.filter_list: 
                self.objects_dict[str(attrs['ref'])] = self.current_dict
                print self.current_dict
        except:
            pass
    ##
    # Called by <code>endElement</code> func when a node tag is closed.
    #    
    def object_end(self):
        return
    def read_objects(self, file):
        self.object_list = []
        while 1:
            l = file.readline()
            if len(l) == 0: break
            if l.find('[') > -1:
                self.object_list = eval(l[:l.find(']')+1])
                break
        supported_object_types = [0,1,2,3,4,5,13,14,19] #ai through mv, no device
        #filter by supported types and then remove object type number from ID, since they make all ID unique regardless of type
        self.object_list = filter(lambda x: x>>22 in supported_object_types, self.object_list)
        self.filter_list = [x & 0x3FFFFF for x in self.object_list] #strip object type info off list
        self.object_type_list = [x >> 22 for x in self.object_list]
        self.object_type_map = dict(zip(self.filter_list, self.object_type_list))

def _copy_dict(dict):
    copy = {}
    for key in dict.keys():
        copy[str(key)] = str(dict[key])
    return copy

##
# @return The root <code>Configuration</code> object from the XML
#         configuration file named <code>fileName</code>.
#
def parse_xml(fileName, ol=None):
    #read the object list file to make a filter for the types of objects we support
    parser = sax.make_parser()
    dh = docHandler()
    #dh.read_objects(ol)
    parser.setContentHandler(dh)
    parser.parse(fileName)
    return dh

def generate_node_urls(dh):
    urls = {}
    for k in dh.objects_dict.keys():
        name = k.split(':')[1] #clean off the beginning of the object name
        name = name.replace('.','/') #convert the .'s into /'s (like a url)
        object_id = int(dh.objects_dict[k]['objectid']) #id portion of bacnet id
        object_type = class_obj[int(dh.objects_dict[k]['classid'])] #look up object type by class id
        #object_type = dh.object_type_map[object_id] #obj type portion of bacnet id
        urls[name] = '/%d/%d' % (object_type, object_id) #this dict contains all we need to construct xml for alias
    return urls

def convert_node_urls_to_tree(urls):
    root = {}
    for url in urls.keys():
        current_dict = root
        for u in url.split('/'):
            if not current_dict.has_key(u):
                current_dict[u]={}
            current_dict = current_dict[u]
        current_dict['__link__'] = urls[url]
    return root

def convert_tree_to_xml(file, tree, name, bacnet_path, depth=0):
    if tree.has_key('__link__'):
        if len(tree.keys()) == 1: #is regular alias point
            s = alias_point % (name, bacnet_path + tree['__link__'])
            s = s.split('\n')
            for l in s:
                file.write('  ' * depth)
                file.write(l + '\n')
            return
        #since an alias group with a link
        file.write('  ' * depth)
        file.write(alias_group_header % (name,))
        s = alias_group_link % (bacnet_path + tree['__link__'],)
        s = s.split('\n')
        for l in s:
            file.write('  ' * depth)
            file.write(l + '\n')
        for k in tree.keys():
            if k == '__link__': continue
            convert_tree_to_xml(file, tree[k], k, bacnet_path, depth+1)
            file.write('  ' * (depth + 1))
            file.write(close_node)
        return
    if name is None:
        file.write(xml_header)
    else:
        file.write('  ' * depth)
        file.write(alias_group_header % (name,))
    for k in tree.keys():
        convert_tree_to_xml(file, tree[k], k, bacnet_path, depth+1)
        file.write('  ' * (depth + 1))
        file.write(close_node)
    return
    
def convert_file(nae_file, bacnet_path):
    f=open(nae_file)
    #ol=open(object_list_file)
    o = parse_xml(f) #, ol)
    f.close()
    #ol.close()
    n = generate_node_urls(o)
    t = convert_node_urls_to_tree(n)
    #extract device ID from tree
    device_id = None
    for v in n.values():
        if v[:3] == '/8/': #find device obj type
            device_id = v[3:]
            break
    if device_id is None:
        raise
    #take the nae xml filename and insert 'alias.' in front of it for the output file name
    path = f.name.split('/') #break apart the path name
    file_name = path.pop().split('.') #basic name
    file_name.insert(0,'alias') #make it 'alias.whatever.xml'
    path.append('.'.join(file_name)) #add changed name to any path
    result_file_name = '/'.join(path) #presto chango
    x = open(result_file_name,'w')

    convert_tree_to_xml(x, t, None, bacnet_path + device_id)

    x.write('</mpxconfig>\r\n')
    x.close()
 
xml_header = "<mpxconfig node_version='1.5.0.dev.11'>\r\n"

alias_group_header = "<node name='%s' node_id='452' module='mpx.service.aliases.factory'  config_builder=''  inherant='false' description='Alias group'>\r\n"

alias_group_link = """  <config>
    <property name='__type__' value='point'/>
    <property name='node_url' value='%s'/>
  </config>
"""

alias_point = """<node name='%s' node_id='257' module='mpx.service.alias.factory'  config_builder=''  inherant='false' description='Alias (another name for an existing node)'>
  <config>
    <property name='__type__' value='point'/>
    <property name='node_url' value='%s'/>
  </config>"""

close_node = "</node>\r\n"

if __name__ == '__main__':
    import sys
    if '-h' in sys.argv or len(sys.argv) < 2:
        print 'Generates an Alias xml snippet from an NAE Export file'
        #print 'and a [list] of the object ID numbers found on a device'
        print 'the resulting file is imported, in the config tool, under:'
        print '   /aliases/'
        #print 'Server Device name must be set to a number.'
        print
        print 'Syntax:'
        print 'nae2alias NAE_export.xml [--bacnet_path path_to_Devices]'
    else:
        bacnet_path = '/services/network/BACnet/internetwork/Devices/'
        if '--bacnet_path' in sys.argv:
            bacnet_path = sys.argv[sys.argv.find('--bacnet_path')+1]
        nae_file = sys.argv[1]
        #object_list_file = sys.argv[2]
        #device_number = sys.argv[2]
        convert_file( nae_file, bacnet_path) # + device_number )

"""
from nae_xml2alias import *

f=open('NAE2export.xml')
ol=open('object_list.txt')
o = parse_xml(f, ol)
f.close()
ol.close()
n = generate_node_urls(o)
t = convert_node_urls_to_tree(n)
x = open('result.xml','w')
convert_tree_to_xml(x, t, None, '/services/network/BACnet/internetwork/Devices/123')
x.write('</mpxconfig>\r\n')
x.close()

"""
