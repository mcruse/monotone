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
import types
from mpx.lib import msglog
from mpx.lib.node import CompositeNode,as_node,as_node_url
from mpx.lib.configure import get_attribute,set_attribute,REQUIRED
from mpx.lib.log import ColumnConfiguration
from mpx.lib.exceptions import ENoData
from mpx.lib.stream import StreamingTupleWithCallback
from mpx.service.logger.periodic_log import PeriodicLog
from mpx.service.logger.periodic_column import PeriodicColumn

class GroupLog(PeriodicLog):
    def start(self):
        timestamp = PeriodicColumn()
        timestamp.configure({'parent':self.get_child('groups'),
                             'name':'timestamp',
                             'position':0,
                             'sort_order':'ascending',
                             'args':(),
                             'function':'self.scheduled_time'})
        self.collector.add_column(timestamp)
        self._groups = []
        for child in self.get_child('groups').children_nodes():
            if child.name != 'timestamp':
                self._groups.append(child)
        configs = [ColumnConfiguration()]
        configs[0].configure(timestamp.configuration())
        self._sort_groups()
        for i in range(0,len(self._groups)):
            group = self._groups[i]
            group.position = i+1
            self.collector.add_column(group)
            mata = {}
            if hasattr(group,'meta'):
                meta = group.meta
            configs.append(ColumnConfiguration(group.name,
                                               group.position,None,
                                               meta))
        self.log.configure(configs, self.minimum_size, self.maximum_size)
        column_data = self.log.data_manager.get_data()
        self._seqs = column_data.keys()
        self._seqs.sort()
        self._seqs.reverse()
        # seqs is list of config seqs starting with latest.
        self._configs = {}
        for seq in self._seqs:
            self._configs[seq] = {}
            for position in column_data[seq]:
                column = column_data[seq][position]
                if column['name'] in ('_seq','timestamp'):
                    continue
                self._configs[seq][column['name']] = column['meta']
        self.collector.start()
        CompositeNode.start(self)
    def _sort_groups(self):
        self._groups.sort(_group_sort)
    def get_range(self,column,start,end):
        stream = StreamingTupleWithCallback(self._get_item_callback,
                                            self._get_length_callback)
        stream.set_meta('data',PeriodicLog.get_range(self,column,start,end,1))
        return stream
    def get_slice(self,column,start,end):
        stream = StreamingTupleWithCallback(self._get_item_callback,
                                            self._get_length_callback)
        stream.set_meta('data',PeriodicLog.get_slice(self,column,start,end,1))
        return stream
    def _get_item_callback(self,index,stream):
        entry = stream.get_meta_value('data')[index]
        seq = self._map_sequence(entry['_seq'])
        del(entry['_seq'])
        for key in entry.keys():
            entry[key] = self._expand_names(seq,key,entry[key])
        return entry
    def _get_length_callback(self,stream):
        return len(stream.get_meta_value('data'))
    def _map_sequence(self,seq):
        for sequence in self._seqs:
            if sequence <= seq:
                break
        return sequence
    def _get_name(self,seq,group,index):
        return self._configs[seq][group]['names'][int(index)]
    def _expand_names(self,seq,group,data):
        if type(data) != types.DictType:
            return data
        expanded = {}
        for key in data.keys():
            expanded[self._get_name(seq,group,key)] = data[key]
        return expanded
class Point:
    def __init__(self,function):
        self._function = function
    def get(self, skipCache=0):
        return self._function()
class PointGroup(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self._points = []
        self.meta = {'names':[]}
    def configure(self,config):
        CompositeNode.configure(self,config)
        set_attribute(self,'points',REQUIRED,config)
        # self._points will later be built in same order.
        # this needs to be done here so that parent's start
        # doesn't have to happend before my start is called.
        for point in self.points:
            self.meta['names'].append(point['name'])
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self,'points',config)
        return config
    def start(self):
        for point in self.points:
            self._add_point(point)
        return CompositeNode.start(self)
    def _add_point(self,point):
        function = as_node(point['node']).get
        self._points.append(Point(function))
    def function(self):
        points = {}
        for i in range(0,len(self._points)):
            point = self._points[i]
            try:
                points[i] = point.get()
            except:
                msglog.exception()
                points[i] = None
        return points
class ChangedPoint(Point):
    def __init__(self,function,tolerance):
        Point.__init__(self,function)
        self._tolerance = tolerance
        self._last = None
    def get(self, skipCache=0):
        value = Point.get(self)
        if ((self._last is not None) and 
            (abs(value - self._last) <= self._tolerance)):
            raise ENoData()
        self._last = value
        return value
class ChangedPointGroup(PointGroup):
    def _add_point(self,point):
        function = as_node(point['node']).get
        tolerance = 0
        if point['tolerance']:
            tolerance = float(point['tolerance'])
        self._points.append(ChangedPoint(function,tolerance))
    def function(self):
        points = {}
        for i in range(0,len(self._points)):
            point = self._points[i]
            try:
                points[i] = point.get()
            except ENoData:
                continue
            except:
                msglog.exception()
                points[i] = None
        return points
def _group_sort(g1,g2):
    if g1.name > g2.name:
        return 1
    if g1.name < g2.name:
        return -1
    return 0



