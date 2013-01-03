"""
Copyright (C) 2010 2011 Cisco Systems

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
from mpx.lib.datatype.serialize.interfaces import IBroadways
from mpx.lib.neode.interfaces import IConfigurableNode
from mpx.lib.node import as_node

snippet = """
      <node name='value' node_id='515' module='mpx.lib.node.simple_value.SimpleValue'  config_builder='' inherant='false' description='Configurable Value'>
        <config>
          <property name='__type__' value='point'/>
          <property name='debug' value='0'/>
          <property name='value' value='1'/>
          <property name='conversion' value='int'/>
        </config>
        <node name='value' node_id='515' module='mpx.lib.node.simple_value.SimpleValue'  config_builder='' inherant='false' description='Configurable Value'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='2'/>
            <property name='conversion' value='int'/>
          </config>
        </node>
      </node>
"""

virtuals = IConfigurableNode(as_node('/interfaces/virtuals'))
vconfig = IBroadways(virtuals)
print vconfig.dumps()
vconfig.loads(snippet)


"""
import StringIO
datastream = StringIO.StringIO()
from mpx.lib.configure._xml_handler import _encode_xml as encode_xml
from mpx.lib.configure import parse_xml
from mpx.lib.configure import Iterator
from mpx.system.system import _load as load_node
datastream.write(snippet)
datastream.seek(0)
xmlroot = parse_xml(datastream)
xmlroot
<mpx.lib.configure._configuration.Configuration instance at 0x4061ec44>
xmlroot.parent
crawler = Iterator(xmlroot)
crawler.root.parent 
crawler.root        
<mpx.lib.configure._configuration.Configuration instance at 0x4061ec44>
xmlnode = crawler.get_next_node()
xmlnode
<mpx.lib.configure._configuration.Configuration instance at 0x4061ec44>
xmlnode.get_config()
{'conversion': 'int', 'name': 'value', 'parent': None, 'config_builder': '', '__type__': 'point', 'module': 'mpx.lib.node.simple_value.SimpleValue', 'node_id': '515', 'value': '1', 'debug': '0', 'inherant': 'false', 'description': 'Configurable Value'}
xmlnode = crawler.get_next_node()
xmlnode.get_config()
{'conversion': 'int', 'name': 'value', 'parent': 'value', 'config_builder': '', '__type__': 'point', 'module': 'mpx.lib.node.simple_value.SimpleValue', 'node_id': '515', 'value': '2', 'debug': '0', 'inherant': 'false', 'description': 'Configurable Value'}
xmlnode.root.get_url()
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
AttributeError: Configuration instance has no attribute 'root'
>>> xmlnode.get_url()
'value/value'
>>> xmlnode.parent = '/interfaces/virtuals'
>>> xmlnode.get_url()
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
  File "/home/dleimbrock/broadway/mpx/lib/configure/_configuration.py", line 69, in get_url
AttributeError: 'str' object has no attribute 'get_url'
>>> 

"""