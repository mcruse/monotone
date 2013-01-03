"""
Copyright (C) 2001 2002 2010 2011 Cisco Systems

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
##
# @import mpx.lib
#
import mpx.lib
##
# This is the Service Ineterface for the logger service.
#
# @implements mpx.service.ServiceInterface
#
class ServiceInterface:
    ##
    # @author Craig Warren
    # @param service
    #   the service object that is going to be used as the logger
    #
    def __init__(self, service):
        self.logger = service
        self.debug = self.logger.debug
        self.msglog = mpx.lib.msglog

        if self.debug:
            msg = '\n'
            msg = msg + 'Package: mpx.service.logger\n'
            msg = msg + 'Class: ServiceInterface\n'
            msg = msg + 'Method: __init__ method\n'
            msg = msg + ' ' + 'self.logger=' + str(self.logger) + '\n'
            msg = msg + ' ' + 'self.msglog=' + str(self.msglog) + '\n'
            self.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)
    
    def children_names(self):
        return self.logger.children_names()
    def children_nodes(self):
        return self.logger.children_nodes()
    def get_child(self,name):
        return self.logger.get_child(name)
    def has_child(self,name):
        return self.logger.has_child(name)
    
    ##
    # @author Craig Warren
    # @param log_name
    #   the name of the log that will be returned
    # @return log
    #   the log object
    #
    def _log(self, log_name):
        return self.logger.get_log(log_name)
        
    ##
    # @author Craig
    # @param log_name
    #   the log to get the range from
    # @param column_name
    #   the column_name that the range gets applied to
    # @param start
    #   the start value of the range
    # @param end
    #   the end value of the range
    # @return  list 
    #   the list of dictionaries are the column_item records that
    #   fall on or between the start and end values that were passed in
    # @exception msglog.exception
    #
    def get_range(self,log_name,column_name,start,end):
        if self.debug:
            msg = 'Package: mpx.service.logger.service_interface\n'
            msg = msg + 'Class: ServiceInterface\n'
            msg = msg + 'Method: get_range\n'
            msg = msg + 'log_name= ' + str(log_name) + '\n'
            msg = msg + 'column_name= ' + str(column_name) + '\n'
            msg = msg + 'start= ' + str(start) + '\n'
            msg = msg + 'end= ' + str(end) + '\n'
            self.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)

        range =[]
        try:
            range = self._log(log_name).get_range(column_name,start,end)
        except:
            self.msglog.exception()
        return range

    ##
    # @author Craig Warren
    # @param log_name
    #   the log to get the slice from
    # @start
    #   the start value of the range
    # @param end
    #   the end value of the range
    # @return  list 
    #   the list of dictionaries are the column_item records that
    #   fall on or between the start and end values that were passed in
    def get_slice(self,column_name, log_name,start,end):
        if self.debug:
            msg = 'Package: mpx.service.logger.service_interface\n'
            msg = msg + 'Class: ServiceInterface\n'
            msg = msg + 'Method: get_slice\n'
            msg = msg + 'log_name= ' + str(log_name) + '\n'
            msg = msg + 'start= ' + str(start) + '\n'
            msg = msg + 'end= ' + str(end) + '\n'
            self.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)
        range = []
        try:
            range = self._log(log_name).get_slice(start,end)
        except:
            self.msglog.exception
        return range

    ##
    # @author Craig Warren
    # @param log_name
    #  the name of the log to get the column names
    # @return list
    #   a list of column names in the order that
    #   they are collected
    #
    def get_columns(self,log_name):
        if self.debug:
            msg = 'Package: mpx.service.logger.service_interface\n'
            msg = msg + 'Class: ServiceInterface'
            msg = msg + 'Method: get_columns'
            msg = msg + 'log_name= ' + str(log_name)
            self.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)
        
        return self._log(log_name).get_columns()

    ##
    # @author Craig Warren
    # @param log_name
    #  the name of the log to describe the columns
    # @return dictionary
    #  a dictionary of the column_names.  The
    #  key in the dictionary is the index order
    #  0 = first logged_item being logged
    #  1 = sec logged_item being logged
    #
    def describe_columns(self,log_name):
        return self._log(log_name).describe_columns()
        
    
    ##
    # @author Craig Warren
    # @param log_name
    #   the name of the log 
    # @param column_name_index
    #    an int that is the index of the column_name to return
    # @return string
    #   the column name
    #
    def get_column_name(self,log_name,column_index):
        return self._log(log_name).get_column_name(column_index)


    ##
    # @author Craig Warren
    # @param log_name
    #  name of the log to preform the trim on
    # @param column_name
    #   column_name to do the trimming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are greater or equal to the value passed in on the
    # column_name that was passed in
    # @return None
    #
    def trim_ge(self,log_name,column_name,value):
        if self.debug:
            msg = 'Package:  mpx.service.logger.service_interface\n'
            msg = msg + 'Class: ServiceInterface\n'
            msg = msg + 'Method: trim_ge\n'
            msg = msg + 'log_name=' + str(log_name) + '\n'
            msg = msg + 'column_name=' + str(column_name) + '\n'
            msg = msg + 'value=' + str(value) + '\n'
            self.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)
            
        self._log(log_name).trim_ge(column_name,value)

    ##
    # @author Craig Warren
    # @param log_name
    #  name of the log to preform the trim on
    # @param column_name
    #   column_name to do the trimming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are greater then the value passed in on the
    # column_name that was passed in
    # @return None
    #
    def trim_gt(self,log_name,column_name,value):
        if self.debug:
            msg = 'Package:  mpx.service.logger.service_interface\n'
            msg = msg + 'Class: ServiceInterface\n'
            msg = msg + 'Method: trim_gt\n'
            msg = msg + 'log_name=' + str(log_name) + '\n'
            msg = msg + 'column_name=' + str(column_name) + '\n'
            msg = msg + 'value=' + str(value) + '\n'
            self.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)

        self._log(log_name).trim_gt(column_name,value)

    ##
    # @author Craig Warren
    # @param log_name
    #  name of the log to preform the trim on
    # @param column_name
    #   column_name to do the trimming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are less or equal to the value passed in on the
    # column_name that was passed in
    # @return None
    #
    def trim_le(self,log_name,column_name,value):
        if self.debug:
            msg = 'Package:  mpx.service.logger.service_interface\n'
            msg = msg + 'Class: ServiceInterface\n'
            msg = msg + 'Method: trim_le\n'
            msg = msg + 'log_name=' + str(log_name) + '\n'
            msg = msg + 'column_name=' + str(column_name) + '\n'
            msg = msg + 'value=' + str(value) + '\n'
            self.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)
            
        self._log(log_name).trim_le(column_name,value)

    ##
    # @author Craig Warren
    # @param log_name
    #  name of the log to preform the trim on
    # @param column_name
    #   column_name to do the triming on
    # @param value
    #   the value to use to preform the trim
    # the log file will be trimmed of all entries
    # that are less then the value passed in on the
    # column_name that was passed in
    # @return None
    #
    def trim_lt(self,log_name,column_name,value):
         if self.debug:
             msg = 'Package:  mpx.service.logger.service_interface\n'
             msg = msg + 'Class: ServiceInterface\n'
             msg = msg + 'Method: trim_lt\n'
             msg = msg + 'log_name=' + str(log_name) + '\n'
             msg = msg + 'column_name=' + str(column_name) + '\n'
             msg = msg + 'value=' + str(value) + '\n'
             self.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)

         self._log(log_name).trim_lt(column_name,value)

    ##
    # @author Craig Warren
    # @param log_name
    #   the log name to return the period from
    # @return float
    #  the nembers of secs of hte period
    #
    def period(self,log_name):
        if self.debug:
            msg = '\n'
            msg = msg + 'Package: mpx.service.logger.service_interface\n'
            msg = msg + 'Class: ServiceInterface\n'
            msg = msg + 'Method: period\n'
            msg = msg + 'log_name=' + str(log_name) + '\n'
            self.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)
            
        return self._log(log_name).period
    
    ##
    # @author Craig Warren
    # @param log_name
    #   the name of the log
    # @return float
    #   the next time that the log is scheduled to collect data, the
    #   value is in secs since the epoch
    #
    def next_scheduled_time(self,log_name):
        if self.debug:
            msg = '\n'
            msg = msg + 'Package: mpx.service.logger.service_interface\n'
            msg = msg + 'Class: ServiceInterface\n'
            msg = msg + 'Method: next_scheduled_time\n'
            msg = msg + 'log name=' + str(log_name) + '\n'
            self.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)

        return self._log(log_name).next_scheduled_time()
    
    ##
    # @author Craig Warren
    # @param log_name
    #   the log to start
    #   if nothing is passed in it starts all the logs
    # @return None
    #
    def start(self,log_name = None):
        self.msglog.log('broadway', mpx.lib.msglog.types.INFO,'starting the logger service')
        if self.debug:
            msg = 'Package: mpx.service.logger.service_interface.py\n'
            msg = msg + 'Class: ServiceInterface\n'
            msg = msg + 'Method: start\n'
            msg = msg + 'log_name=' + str(log_name)
        if log_name:
            self._log(log_name).start()
        else:
            self.logger.start()

    ##
    # @author Craig Warren
    # @param log_name
    #    the log to start
    #    fi nothing is passed in it stops all the logs
    # @return None
    #
    def stop(self,log_name = None):
        self.msglog.log('broadway', mpx.lib.msglog.types.INFO,'stoping the ' \
                        + 'logger service')

        if self.debug:
            msg = 'Package: mpx.service.logger.service_interface.py\n'
            msg = msg + 'Class: ServiceInterface\n'
            msg = msg + 'Method: stop\n'
            msg = msg + 'log_name=' + str(log_name)
            self.msglog.log('broadway', mpx.lib.msglog.types.DB,msg)

        if log_name:
            self._log(log_name).stop()
        else:
            self.logger.stop()
            
          
    ##
    # @author Craig Warren
    # @NotImplementedYet
    # Get the configuration dictionary.
    #
    def configuration(self):
        return self.logger.configuration()
    
    ##
    # @author Craig Warren
    # @NotImplementedYet
    # Clear all data from the log.
    #
    def clear(self,log_name):
        return

    ##
    # @author Craig Warren
    # @NotImplementedYet
    # Destroy the current log, data and configuration.
    #
    def destroy(self,log_name):
        return
