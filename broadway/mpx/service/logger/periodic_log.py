"""
Copyright (C) 2001 2002 2004 2006 2010 2011 Cisco Systems

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

from collector import Collector
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.exceptions import EInvalidValue, ENotImplemented
from mpx.lib.security import RExec
from log import Log
import mpx.lib
from mpx.lib.stream import StreamingTupleWithCallback

def _create_shared_env():
    import mpx.lib.node
    class Temp:
        __module__ = __name__

    stub = Temp()
    stub.lib = Temp()
    stub.lib.node = Temp()
    stub.lib.node.as_node = mpx.lib.node.as_node
    stub.lib.node.as_internal_node = mpx.lib.node.as_internal_node
    rexec = RExec()
    rexec.update_global_names({'mpx': stub,
     'as_node': mpx.lib.node.as_node,
     'as_internal_node': mpx.lib.node.as_internal_node})
    return rexec


class _IntervalStreamFilter:
    __module__ = __name__

    def __init__(self, interval, stream):
        self._stream = stream
        self._interval = interval
        self._index = 0
        self.__getitem__ = self._getitem
        try:
            self._bounds = {1: self._stream[0],
             -1: self._stream[-1]}
        except IndexError:
            self.__getitem__ = self._raise_error



    def _raise_error(self, index):
        raise IndexError()



    def _getitem(self, index):
        if (index == 0):
            return self._bounds[1]
        elif (index < 0):
            if (index == -1):
                return self._bounds[-1]
            index += 1
        timestamp = (self._bounds[(index / abs(index))]['timestamp'] + (index * self._interval))
        entry = self._stream[self._index]
        difference = (timestamp - entry['timestamp'])
        direction = (difference / abs(difference))
        while (entry['timestamp'] != timestamp):
            self._index += direction
            entry = self._stream[self._index]

        return entry



    def __getslice__(self, start, end):
        values = []
        index = start
        try:
            while (index < end):
                values.append(self.__getitem__(index))
                index += 1

        except IndexError:
            pass
        return values



    def __len__(self):
        if (self.__getitem__ is self._raise_error):
            return 0
        raise ENotImplemented()



class PeriodicLog(Log):
    __module__ = __name__

    def __init__(self):
        self._r_env = _create_shared_env()
        Log.__init__(self)
        self.collector = None
        self.trigger = None


    def get_environment(self):
        return self._r_env



    def configure(self, config):
        if config.has_key('trigger'):
            self.trigger = config['trigger']
        set_attribute(self, 'period', REQUIRED, config, int)
        Log.configure(self, config)



    def configuration(self):
        config = Log.configuration(self)
        get_attribute(self, 'period', config, str)
        if self.trigger:
            get_attribute(self, 'trigger', config, str)
        return config



    def _add_child(self, node):
        Log._add_child(self, node)



    def _column_names(self):
        name_list = []
        for child in self.collector.columns:
            name_list.append(child.name)

        return name_list



    def get_range(self, column_name, start, end, extended = 0):
        if self.debug:
            msg = 'Package: /mpx/services/logger\n'
            msg = (msg + 'Class: PeriodicLog\n')
            msg = (msg + 'Method: get_range\n')
            msg = (((msg + 'column_name= ') + str(column_name)) + '\n')
            msg = (((msg + 'start= ') + str(start)) + '\n')
            msg = (((msg + 'end= ') + str(end)) + '\n')
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB, msg)
        return self.log.get_range(column_name, start, end, extended)



    def get_slice_on_interval(self, column, start, end, interval, extended = 0):
        stream = self.log.get_slice(column, start, end, extended)
        return _IntervalStreamFilter(interval, stream)



    def get_slice(self, column, start, stop, extended = 0):
        return self.log.get_slice(column, start, stop, extended)



    def get_last_record(self):
        return self.log.get_last_record()



    def get_first_record(self):
        return self.log.get_first_record()

    def get_last_logged_value(self, column_name):
        last_record = self.log.get_last_record()
        if last_record:
            if last_record.has_key(column_name):
                rtValue = last_record[column_name]
            else:
                rtValue = None
        else:
            rtvalue = None
        return rtValue



    def get_first_logged_value(self, column):
        first_record = self.log.get_first_record()
        if first_record:
            return first_record[column]
        return None



    def get_columns(self):
        return self.log.get_columns()



    def get_column_names(self):
        return self._column_names()



    def describe_columns(self):
        return self.log.describe_columns()



    def get_column_name(self, column_index):
        return self.log.get_column_name(column_index)



    def trim_ge(self, column_name, value):
        if self.debug:
            msg = ((('calling trim_ge on LOG: COLUMN: ' + str(column_name)) + ' VALUE: ') + str(value))
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB, msg)
        self.log.trim_ge(column_name, value)



    def trim_gt(self, column_name, value):
        if self.debug:
            msg = ((('calling trim_gt on LOG: COLUMN: ' + str(column_name)) + ' VALUE: ') + str(value))
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB, msg)
        self.log.trim_gt(column_name, value)



    def trim_le(self, column_name, value):
        if self.debug:
            msg = ((('calling trim_le on LOG: COLUMN: ' + str(column_name)) + ' VALUE: ') + str(value))
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB, msg)
        self.log.trim_le(column_name, value)



    def trim_lt(self, column_name, value):
        if self.debug:
            msg = ((('calling trim_lt on LOG: COLUMN: ' + str(column_name)) + ' VALUE: ') + str(value))
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB, msg)
        self.log.trim_lt(column_name, value)



    def start(self):
        if self.debug:
            msg = 'Package: mpx.service.logger.periodic_log\n'
            msg = (msg + 'Class: PeriodicLog\n')
            msg = (msg + 'Method: start')
            msg = (msg + 'starting the periodic log collecting...')
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB, msg)
        if (self.collector is not None):
            self.collector.stop()
        self.collector = Collector(self, self.period, self.trigger)
        for node in self.get_child('columns').children_nodes():
            self.collector.add_column(node)

        Log.start(self)
        self.collector.start()



    def stop(self):
        if self.debug:
            msg = 'Package: mpx.service.logger.periodic_log\n'
            msg = (msg + 'Class: PeriodicLog\n')
            msg = (msg + 'Method: start')
            msg = (msg + 'stopping the periodic log collecting...')
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB, msg)
        if (self.collector != None):
            self.collector.stop()
            self.collector = None
        Log.stop(self)



    def next_scheduled_time(self):
        return self.collector.next_scheduled_time()



    def scheduled_time(self):
        return self.collector.scheduled_time()




def factory():
    return PeriodicLog()



