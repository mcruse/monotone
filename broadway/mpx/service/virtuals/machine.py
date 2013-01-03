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
import random
from mpx.componentry import implements
from mpx.lib import EnumeratedValue
from mpx.lib import msglog
from mpx.lib.simulator import point as simulators
from mpx.lib.metadata.interfaces import IMetaDataProvider
from mpx.lib.neode.node import CompositeNode
from mpx.lib.neode.node import ConfigurableNode
from interfaces import IMachine
from interfaces import IPoint

class MetaDataNode(ConfigurableNode):
    def configure(self, config):
        metadata = config.get('metadata', [])
        metaprovider = IMetaDataProvider(self)
        for datum in metadata:
            name, value = datum['name'], datum['definition']
            metaprovider[name] = value
        super(MetaDataNode, self).configure(config)
    def configuration(self):
        config = super(MetaDataNode, self).configuration()
        metaprovider = IMetaDataProvider(self)
        metadata = []
        for name,value in metaprovider.get_items():
            metadata.append({'name':name,'definition':value})
        config['metadata'] = metadata
        return config

class Machine(CompositeNode, MetaDataNode):
    implements(IMachine)
    
    def __init__(self, *args, **kw):
        self.scalarcount = 0
        super(Machine, self).__init__(*args, **kw)
    def start(self):
        return CompositeNode.start(self)
    def stop(self):
        return CompositeNode.stop(self)
    def start_simulation(self):
        for point in self.children_nodes():
            point.start_simulation()
        return
    def stop_simulation(self):
        for point in self.children_nodes():
            poin.stop_simulation()
        return

class Point(MetaDataNode):
    implements(IPoint)
    
    def __init__(self, *args):
        self.node = ''
        self.mode = 'normal'
        self._node = None
        self._simulator = None
        self._override = None
        super(Point, self).__init__(*args)
    def configure(self, config):
        self.node = config.get('node', self.node)
        super(Point, self).configure(config)
    def configuration(self):
        config = super(Point, self).configuration()
        config['node'] = self.node
        if self.mode == 'simulation':
            config['simulator'] = str(self._simulator)[1:-1]
        return config
    def start_simulation(self):
        metadataprovider = IMetaDataProvider(self)
        point_type = metadataprovider.get_meta('point_type', 'scalar')
        point_value = metadataprovider.get_meta('value', 0)
        if point_type == 'scalar':
            self.parent.scalarcount += 1
            try: 
                minvalue = int(point_value)
            except ValueError: 
                minvalue = float(point_value)
            maxvalue = 100
            stepvalue = 1
            upmagnitude = not (self.parent.scalarcount % 5)
            if upmagnitude:
                minvalue += 500
                maxvalue *= 10
            oddscalar = self.parent.scalarcount % 2
            if oddscalar:
                step = 0.5
            minvalue = metadataprovider.get_meta('min', str(minvalue))
            maxvalue = metadataprovider.get_meta('max', str(maxvalue))
            stepvalue = metadataprovider.get_meta('step', str(stepvalue))
            scalartype = simulators.SequentialInteger
            conversion = int
            try: 
                minvalue = int(minvalue)
            except ValueError: 
                conversion = float
                minvalue = float(minvalue)
                scalartype = simulators.SequentialNumber
            try:
                maxvalue = int(maxvalue)
            except ValueError:
                conversion = float
                maxvalue = float(maxvalue)
                scalartype = simulators.SequentialNumber
            try:
                stepvalue = int(stepvalue)
            except ValueError:
                conversion = float
                stepvalue = float(stepvalue)
                scalartype = simulators.SequentialNumber
            #self.scalarconversion = conversion
            # Overriding for demonstration which uses all floats.
            self.scalarconversion = float
            self._simulator = scalartype(minvalue, maxvalue, stepvalue)
        elif point_type == 'enumeration':
            values = point_value.keys()
            values.sort()
            names = map(point_value.get, values)
            enumerations = map(EnumeratedValue, values, names)
            self._simulator = simulators.SequentialEnumeration(enumerations)
        self.pointtype = point_type
        periodvalue = 15
        periodvalue = metadataprovider.get_meta('period', str(periodvalue))
        try:
            periodvalue = int(periodvalue)
        except ValueError:
            periodvalue = float(periodvalue)
        self._simulator = simulators.PeriodicModifier(self._simulator, periodvalue)
        self.mode = 'simulation'
    def stop_simulation(self):
        self.mode = 'normal'
    def _get_node(self):
        if self._node is None:
            if not self.node:
                raise TypeError('Point node was not configured.')
            self._node = self.nodespace.as_node(self.node)
        return self._node
    ##
    # Unfortunately the Aliases branch does not propogate the start call.
    #   To avoid the possibility of breaking existing code, the start method 
    #   here does not resolve the node to which the Point points; that is 
    #   done on the fly in a lazy fashion instead via a controlled property.
    def start(self):
        self._node = None
        if self.node in ('', 'REQUIRED'):
            self.start_simulation()
        return super(Point, self).start()
    def stop(self):
        self._node = None
        return super(Point, self).stop()
    def get(self, *args):
        if self.mode == 'simulation':
            if self._override is not None:
                return self._override
            return self._simulator.get()
        node = self._get_node()
        if node is None:
            raise AttributeError('Point does not reference node.  Get not available.')
        return node.get(*args)
    def set(self, *args):
        if self.mode == 'simulation':
            value = args[0]
            try:
                if self.pointtype == 'scalar':
                    value = self.scalarconversion(value)
                elif self.pointtype == 'enumeration':
                    value = self._simulator.get_enumeration(value)
            except: 
                msglog.exception()
            self._override = value
        else:
            node = self._get_node()
            if node is None:
                raise AttributeError('Point does not reference node.  Set not available.')
            return node.set(*args)
