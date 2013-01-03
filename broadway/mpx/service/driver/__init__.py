"""
Copyright (C) 2007 2008 2010 2011 Cisco Systems

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
import interfaces
import adapters
from mpx.lib.driver import PeriodicDriver
from mpx.componentry import implements
from mpx.lib.neode.node import ConfigurableNode
from mpx.lib.neode.node import CompositeNode
from mpx.lib.node import as_node
from interfaces import IPeriodicDriverManager
from interfaces import IPeriodicDriver
from interfaces import IMultiPlexor

class PeriodicDriverManager(CompositeNode):
    implements(IPeriodicDriverManager)
    ##
    # Needed because children may end up being hybrids between 
    # old-style nodes and neode-style nodes.
    def _add_child(self, child): 
        pass

class ValueDriver(CompositeNode, PeriodicDriver):
    implements(IPeriodicDriver)
    
    def __init__(self, *args):
        CompositeNode.__init__(self, *args)
        PeriodicDriver.__init__(self)
        self.outputs = []
        self._resolved = []
        self._unresolved = []
    def configure(self, config):
        CompositeNode.configure(self, config)
        outputs = config.get('outputs', self.outputs)
        self.outputs = filter(None, outputs)
        if not self.has_child('Fan Out'):
            multiplexor = self.nodespace.create_node(MultiPlexor)
            multiplexor.configure({'name': 'Fan Out', 'parent': self})
        multiplexor = self.get_child('Fan Out')
        multiplexor.configure({'nodes': self.outputs})
        config['output'] = multiplexor
        PeriodicDriver.configure(self, config)
    def configuration(self):
        config = PeriodicDriver.configuration(self)
        config.update(CompositeNode.configuration(self))
        if config.has_key('output'):
            del(config['output'])
        outputs = self.outputs[:]
        while len(outputs) < 10:
            outputs.append('')
        config['outputs'] = outputs
        return config
    def start(self):
        self._output_cnt = len(self.outputs)
        PeriodicDriver.start(self)
        CompositeNode.start(self)
    def stop(self):
        PeriodicDriver.stop(self)
        CompositeNode.stop(self)
    def _output(self, value):
        for target_value in self.output.get():
            if target_value != value:
                self.output.set(value)
                break
        self._value = value

class MultiPlexor(ConfigurableNode):
    implements(IMultiPlexor)
    
    def __init__(self, *args):
        self.nodes = []
        self._resolved = []
        self._unresolved = []
        super(MultiPlexor, self).__init__(*args)
    def configure(self, config):
        self.nodes = config.get('nodes', self.nodes)
        return super(MultiPlexor, self).configure(config)
    def configuration(self):
        config = super(MultiPlexor, self).configuration()
        config['nodes'] = self.nodes[:]
        return config
    def start(self):
        resolved, unresolved = [], []
        for url in self.nodes:
            try: 
                resolved.append(self.nodespace.as_node(url))
            except KeyError: 
                unresolved.append(url)
        self._resolved = resolved
        self._unresolved = unresolved
        return super(MultiPlexor, self).start()
    def stop(self):
        super(MultiPlexor, self).stop()
        self._resolved = []
        self._unresolved = []
    def set(self, *args):
        results = []
        for node in self._resolved:
            try: 
                results.append(node.set(*args))
            except Exception, error:
                results.append(error)
        return results
    def get(self, *args):
        results = []
        for node in self._resolved:
            try:
                results.append(node.get())
            except Exception, error:
                results.append(error)
        return results
