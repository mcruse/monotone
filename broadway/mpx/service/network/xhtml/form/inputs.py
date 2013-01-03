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
import time
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import CompositeNode

class Input(CompositeNode):
    def __init__(self, *args):
        self.value = None
        super(Input, self).__init__(*args)
    def configure(self, config):
        self.value = config.get('value', self.value)
        super(Input, self).configure(config)
    def configuration(self):
        config = super(Input, self).configuration()
        config['value'] = self.value
        return config
    def set(self, value):
        self.value = value
    def get(self):
        return self.value
    def __repr__(self):
        classname = type(self).__name__
        nodename = self.name
        return '<%s instance "%s" at %#x>' % (classname, nodename, id(self))

class TextInput(Input):
    def set(self, value):
        return super(TextInput, self).set(str(value))

class NodeInput(Input):
    def __init__(self, *args, **kw):
        self.node = None
        self.nodeurl = None
        super(NodeInput, self).__init__(*args, **kw)
    def configure(self, config):
        self.nodeurl = config.get('nodeurl', self.nodeurl)
        super(NodeInput, self).configure(config)
    def configuration(self):
        config = super(NodeInput, self).configuration()
        config['nodeurl'] = self.nodeurl
        return config
    def start(self):
        self.node = as_node(self.nodeurl)
        super(NodeInput, self).start()
    def set(self, value):
        raise Attribute('NodeInput is read-only')
    def get(self):
        return str(self.node.get())

class AndoverInput(NodeInput):
    """
        Adds behaviour that failed attempts to get node 
        value result in returning of -1.  This value was 
        discussed with Roth Engineering as the value that 
        would be used to indicate a failure.
    """
    def get(self, *args, **kw):
        try:
            value = super(AndoverInput, self).get(*args, **kw)
        except:
            msglog.log('broadway', msglog.types.WARN, 
                       'Input "%s" node-get failed, using -1' % self.name)
            msglog.exception(prefix='handled')
            value = str(-1)
        return value

class TimeInput(Input):
    def __init__(self, *args):
        self.format = ''
        super(TimeInput, self).__init__(*args)
    def configure(self, config):
        self.format = config.get('format', self.format)
        super(TimeInput, self).configure(config)
    def configuration(self):
        config = super(TimeInput, self).configuration()
        config['format'] = self.format
        return config
    def set(self, timestamp):
        if isinstance(timestamp, (int, float)):
            timestamp = time.strftime(self.format, time.localtime(timestamp))
        return super(TimeInput, self).set(timestamp)

class TimeNodeInput(NodeInput, TimeInput):
    def get(self):
        timestamp = self.node.get()
        TimeInput.set(self, timestamp)
        return TimeInput.get(self)


