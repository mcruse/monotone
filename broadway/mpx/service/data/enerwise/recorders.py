"""
Copyright (C) 2003 2010 2011 Cisco Systems

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

from mpx.lib.exceptions import EConfiguration
from mpx.lib.node import CompositeNode,as_node,\
     as_node_url,ConfigurableNode
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED
from mpx.service.logger.periodic_log import PeriodicLog
from mpx.service.logger.periodic_column import PeriodicColumn
from mpx.lib.log import ColumnConfiguration
from mpx.service.data import Formatter

def _sort(r1, r2):
    return (r1.sequence - r2.sequence)

class RecorderSet(PeriodicLog):
    def start(self):
        CompositeNode.start(self)
        next_position = 0
        timestamp = PeriodicColumn()
        timestamp.configure({'parent':self.get_child('recorders'),
                             'name':'timestamp',
                             'position':next_position,
                             'sort_order':'ascending',
                             'args':(),
                             'function':self.scheduled_time})
        timestamp.sequence = 0
        sequences = []
        for child in self.get_child('recorders').children_nodes():
            if child.__class__ == Recorder:
                if child.sequence in sequences:
                    raise EConfiguration(
                        'Conflicting RecorderSet sequence %s on %r' %
                        (child.sequence, child.name))
            sequences.append(child.sequence)
        # Force Timestamp as column '0'.
        self.collector.add_column(timestamp)
        children = self.get_child('recorders').children_nodes()
        children.sort(_sort)
        for child in children:
            if child.__class__ == Recorder:
                for channel in child.channels():
                    next_position += 1
                    channel.position = next_position
                    self.collector.add_column(channel)
        cc = ColumnConfiguration()
        cc.configure(timestamp.configuration())
        self.log.configure([cc]+self.collector.columns[1:],
                           self.minimum_size,self.maximum_size)
        self.collector.start()
class Recorder(CompositeNode):
    def start(self):
        CompositeNode.start(self)
        for i in range(0,4):
            label = getattr(self,'label%s' % (i+1,))
            point = getattr(self,'point%s' % (i+1,))
            if point:
                node = as_node(point)
            else:
                node = None
            self._channels.append(_Channel(i,self.id,label,node))
        return
    def configure(self,config):
        CompositeNode.configure(self,config)        
        set_attribute(self,'sequence',REQUIRED,config,int)
        set_attribute(self,'id',self.name,config)
        set_attribute(self,'unit','KW',config)
        set_attribute(self,'label1','',config)
        set_attribute(self,'label2','',config)
        set_attribute(self,'label3','',config)
        set_attribute(self,'label4','',config)
        set_attribute(self,'point1','',config)
        set_attribute(self,'point2','',config)
        set_attribute(self,'point3','',config)
        set_attribute(self,'point4','',config)
        self._channels = []
        return
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self,'id',config,str)
        get_attribute(self,'unit',config)
        get_attribute(self,'label1',config)
        get_attribute(self,'label2',config)
        get_attribute(self,'label3',config)
        get_attribute(self,'label4',config)
        set_attribute(self,'point1',config)
        set_attribute(self,'point2',config)
        set_attribute(self,'point3',config)
        set_attribute(self,'point4',config)
        return config
    def channels(self):
        return self._channels
    def channel_labels(self):
        labels = []
        for channel in self.channels():
            labels.append(channel.label())
        return labels
    def values(self,entry):
        values = [entry['timestamp']]
        for channel in self.channels():
            try:
                values.append(entry[channel.name])
            except KeyError:
                values.append(None)
        return values
class _Channel(ColumnConfiguration):
    def __init__(self,position,id,name,node):
        self._node = node
        self._label = name
        ColumnConfiguration.__init__(self,(id + '_' + str(position)),position)
    def function(self):
        if self._node:
            return self._node.get()
        return None
    def label(self):
        return self._label
class RecorderFormatter:
    def __init__(self,recorder,time_function=time.gmtime,id_width=15,unit_width=5):
        self.recorder = recorder
        self.id = recorder.id
        self.unit = recorder.unit
        self.interval = int(recorder.parent.parent.period/60)
        self.labels = recorder.channel_labels()
        self.entries = []
        self.time_function = time_function
        self.id_width = id_width
        self.unit_width = unit_width
        return
    def add_entry(self,entry):
        self.entries.append(entry)
        return
    def date(self, ts):
        return time.strftime("%m%d%y,%H%M",self.time_function(ts))
    def output(self):
        result = '"RECORDER ID"," DATE"," HOUR"," IN"," UN"'
        for label in self.labels:
            result = '%s,"%s"' % (result, label)
        result = '%s\n' % (result,)
        for entry in self.entries:
            result = '%s"%-15s"' % (result, self.id)
            result = '%s,%s' % (result, self.date(entry.pop(0)))
            result = '%s,%s' % (result, self.interval)
            result = '%s,"%5s"' % (result, self.unit)
            for value in entry:
                if value is None:
                    value = 0
                result = '%s, %s' % (result, int(value))
            result = '%s\n' % (result,)
        return result
class RecorderSetFormatter(Formatter):
    def start(self):
        self._recorders = []
        recorders = self.parent.parent.parent.get_child('recorders')
        for recorder in recorders.children_nodes():
            if recorder.__class__ == Recorder:
                self._recorders.append(recorder)
        Formatter.start(self)
    def format(self,data):
        formatters = []
        for recorder in self._recorders:
            formatters.append(RecorderFormatter(recorder,self.parent.time_function))
        for entry in data:
            for formatter in formatters:
                formatter.add_entry(formatter.recorder.values(entry))
        output = formatters[0].output()
        for formatter in formatters[1:]:
            output += formatter.output()
        return output

