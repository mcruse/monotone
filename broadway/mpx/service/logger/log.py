"""
Copyright (C) 2001 2002 2003 2007 2008 2009 2010 2011 Cisco Systems

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

import mpx.lib

from mpx.service import ServiceNode

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.event import EventConsumerAbstract
from mpx.lib.event import EventProducerMixin

from mpx.lib.exceptions import EConfiguration

from mpx.lib.log import ColumnConfiguration
from mpx.lib.log import LogEvent
from mpx.lib.log import LogObjectInfo

from mpx.lib.tzinfo import get_tzinfo_range
from mpx.lib.tzinfo import LocalTZInfo

class LogNodeInfo(LogObjectInfo):
    def __init__(self, log_node):
        LogObjectInfo.__init__(self, log_node)
        self.configuration = log_node.configuration()
        self.current_timestamp = time.time()
        self.tzinfo_range = get_tzinfo_range(LocalTZInfo,
                                             self.first_record['timestamp'],
                                             (self.last_record['timestamp']+
                                              LocalTZInfo.YEAR+
                                              LocalTZInfo.DAY+1))
        return
    def as_dict(self):
        result = LogObjectInfo.as_dict(self)
        for attr in ('configuration', 'current_timestamp'):
            result[attr] = getattr(self,attr)
        result['tzinfo_range'] = map(lambda tzi: tzi.as_dict(),
                                     self.tzinfo_range)
        return result
    def __repr__(self):
        return repr(self.as_dict())

class Log(ServiceNode,EventProducerMixin):
    ##
    # Consume all LogEvents from the low-level log object and re-broadcast the
    # events as the source.
    class LogEventFowarder(EventConsumerAbstract):
        def __init__(self, generator):
            EventConsumerAbstract.__init__(self)
            self.generator = generator
            self.log_object = None
            return
        def event_handler(self,log_event):
            generator_event = log_event.clone()
            generator_event.source = self.generator
            self.generator.event_generate(generator_event)
            return
        def start_forwarding(self, log_object):
            if self.log_object is None:
                self.log_object = log_object
                log_object.event_subscribe(self, LogEvent)
            return
        def stop_forwarding(self, log_object):
            log_object = self.log_object
            if log_object is not None:
                self.log_object = None
                log_object.event_unsubscribe(self, LogEvent)
            return
    def __init__(self):
        ServiceNode.__init__(self)
        EventProducerMixin.__init__(self)
        self.forwarder = self.LogEventFowarder(self)
        return
    def nodebrowser_handler(self, nb, path, node, node_url):
        sections = nb.get_default_presentation(node, node_url)
        if not sections['node-persistence']: #blank persistence
            block = ['<div class="node-section node-persistence">']
            block.append('<h2 class="section-name">Persistence</h2>')
            block.append('<ul class="pdo-details">')
            filename = self.log.data_manager._persistent.filename
            block.append("filename = %s" % filename)
            block.append("</ul>")
            block.append("</div>")
            # put html into dict for presentation
            sections['node-persistence'] = "\n".join(block)
        # format sections into html string
        return nb.get_default_view_for(sections)
    ##
    # @author Craig Warren
    # @param config  a configuration dictionary
    # @return None
    def configure(self,config): 
        ServiceNode.configure(self,config)
        set_attribute(self, 'minimum_size', 250, config, int)
        set_attribute(self, 'maximum_size', 500, config, int)
        self.log = mpx.lib.log.TrimmingLog(self.name)
        return
    ##
    # @author Craig Warren
    # @return
    #   returns the current configuration in a
    #   configuration dictionary    
    def configuration(self):
        config = ServiceNode.configuration(self)
        get_attribute(self, 'minimum_size', config, str)
        get_attribute(self, 'maximum_size', config, str)
        return config

    def add_entry(self,values):
        return self.log.add_entry(values)
    
    def get_last_record(self):
        return self.log.get_last_record()

    def get_first_record(self):
        return self.log.get_first_record()

    def get_info(self):
        return LogNodeInfo(self)

    ##
    # @author Craig
    # @param column_name
    #   the column_name that the range gets applied to
    # @param start
    #   the start value of the range
    # @param end
    #   the end value of the range
    # @return a list of dictionaries
    #   the list of dictionaries are the column_item records that
    #   fall on or between the start and end values that were passed in
    def get_range(self,column_name,start,end,extended=0):

        if self.debug:
            msg = 'Package: /mpx/services/logger\n'
            msg = msg + 'Class: PeriodicLog\n'
            msg = msg + 'Method: get_range\n'
            msg = msg + 'column_name= ' + str(column_name) + '\n'
            msg = msg + 'start= ' + str(start) + '\n'
            msg = msg + 'end= ' + str(end) + '\n'
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)    

        return self.log.get_range(column_name,start,end,extended)
    ##
    # @author Craig
    # @param start
    #   the start value of the range
    # @param end
    #   the end value of the range
    # @return a list of dictionaries
    #   the list of dictionaries are the records that
    #   fall on start and less then end
    def get_slice(self,column_name,start,end,extended=0):
        if self.debug: 
            msg = 'Package: /mpx/services/logger\n'
            msg = msg + 'Class: PeriodicLog\n'
            msg = msg + 'Method: get_slice\n'
            msg = msg + 'start= ' + str(start) + '\n'
            msg = msg + 'end= ' + str(end) + '\n'
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)    
        return self.log.get_slice(column_name, start,end,extended)
    
    def get_slice_values(self,column_name,start,end):
        return self.log.get_slice_values(column_name,start,end)
    def get_range_values(self, column_name, start, end):
        return self.log.get_range_values(column_name,start,end)
    
    ##
    # @author Craig Warren
    # @return the last logged value for that column, None if it hasn't been
    # logged
    def get_last_logged_value(self,column_name):
        last_record = self.log.get_last_record()
        if last_record:
            if last_record.has_key(column_name):
                return last_record[column_name]
        return None

     ##
    # @author Craig Warren
    # @return list
    #   a list of column names in the order that
    #   they are collected
    def get_columns(self):
        return self.log.get_column_names()


    ##
    # @author Craig Warren
    # @return dictionary
    #  a dictionary of the column_names.  The
    #  key in the dictionary is the index order
    #  0 = first logged_item being logged
    #  1 = second logged_item being logged
    #
    def describe_columns(self):
        return self.log.describe_columns()


    ## 
    # @author Craig Warren
    # @return list of column name strings in 
    #         the order selected
    #
    def get_column_names(self):
        return self._column_names()
    
    ##
    # @author Craig Warren
    # @param column_name_index
    #    an int that is the index of the column_name to return
    # @return string
    #   the column_name
    def get_column_name(self,column_index):
        return self.log.get_column_name(column_index)

    ##
    # @author Craig Warren
    # @param column_name
    #   column_name to do the trimming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are greater or equal to the value passed in on the
    # column_name that was passed in
    # @return None
    def trim_ge(self,column_name,value):
        if self.debug:
            msg = 'calling trim_ge on LOG: COLUMN: ' + \
                  str(column_name) + ' VALUE: ' + str(value)
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)            
        self.log.trim_ge(column_name,value)

    ##
    # @author Craig Warren
    # @param column_name
    #   column_name to do the trimming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are greater then the value passed in on the
    # column_name that was passed in
    # @return None
    def trim_gt(self,column_name,value):
        if self.debug:
            msg = 'calling trim_gt on LOG: COLUMN: ' + \
                  str(column_name) + ' VALUE: ' + str(value)
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)

        self.log.trim_gt(column_name,value)

    ##
    # @author Craig Warren
    # @param column_name
    #   column_name to do the trimming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are less or equal to the value passed in on the
    # column_name that was passed in
    # @return None
    def trim_le(self,column_name,value):
        if self.debug:
            msg = 'calling trim_le on LOG: COLUMN: ' + \
                  str(column_name) + ' VALUE: ' + str(value)
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)
            
        self.log.trim_le(column_name,value)
        
    ##
    # @author Craig Warren
    # @param column_name
    #   column_name to do the triming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are less then the value passed in on the
    # column_name that was passed in
    # @return None
    def trim_lt(self,column_name,value):
        if self.debug:
            msg = 'calling trim_lt on LOG: COLUMN: ' + \
                  str(column_name) + ' VALUE: ' + str(value)
            mpx.lib.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)
        self.log.trim_lt(column_name,value)

    def _column_names(self):
        return self.get_child('columns').children_names()
    def __getslice__(self,start,end):
        return self.log[start:end]
    def __getitem__(self, index):
        return self.log[index]
    def get_column_names(self):
        return self.get_columns()
    
    def start(self):
        if self.has_child('columns'):
            _positions = []
            columns = []
            for child in self.get_child('columns').children_nodes():
                if child.position in _positions:
                    raise EConfiguration(('One or more columns ' + 
                                          'have the same position'))
                _positions.append(child.position)
                column = ColumnConfiguration()
                column.configure(child.configuration())
                columns.append(column)
            _positions.sort()
            if _positions != range(0,len(_positions)):
                raise EConfiguration((
                    'Columns do not have consecutive positions this '
                    'can be caused by having two columns with the same name.'
                    ))
            self.log.configure(columns,self.minimum_size,self.maximum_size)
        else:
            self.log.set_limits(self.minimum_size,self.maximum_size)
        self.log.start_trimming() # Turn log trimming on now that sizes are set
        self.forwarder.start_forwarding(self.log)
        ServiceNode.start(self)
        return
    def stop(self):
        self.forwarder.stop_forwarding(self.log)
        ServiceNode.stop(self)
        return
##
# @author Craig Warren
# @return log
#  returns and instanciated Log
#
def factory():
    return Log()
