"""
Copyright (C) 2001 2002 2003 2004 2006 2010 2011 Cisco Systems

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
import string
import time
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED
from mpx.lib.security import RFunction
from mpx.lib.node import as_node_url,as_node
from mpx.lib.exceptions import *
from mpx.lib.magnitude import as_magnitude
from mpx.lib.threading import Lock
from mpx.lib import msglog
from mpx.lib.event import EventConsumerMixin
from mpx.service.subscription_manager._manager import SUBSCRIPTION_MANAGER as SM
from column import Column

debug = 0
def _none(object):
    return object
_conversions = {'string':str,
               'float':float,
               'integer':int,
               'magnitude':as_magnitude,
               'long':long,
                'none':_none}
def _function(name):
    return _conversions[name]
def _name(function):
    for name,func in _conversions.items():
        if func == function:
            return name
    raise KeyError(function)

class PeriodicColumn(Column, EventConsumerMixin):
    def __init__(self):
        self.function = None
        self._calculator = None
        self.__node = None
        self.__node_url = None
        self.__lock = Lock()
        self.__started = 0
        self._sid = None
        self._present_value = None
        Column.__init__(self)
        EventConsumerMixin.__init__(self, self.change_of_value)
    ##
    # @author Craig Warren
    # @param config
    #   @key context Sets the context for the function passed in
    #   @value anything Possible context 'import time' because the function
    #                 uses the time modual
    #   @default None
    #   @key function Function to return the value to record
    #   @value function
    #   @required
    #   @key args Arguments to the function
    #   @value list a list of arguments required by the function
    #   @default an empty list
    # @return None
    #
    def configure(self,config):
        Column.configure(self,config)
        set_attribute(self,'context','None',config,str)
        set_attribute(self,'function', REQUIRED, config)
        set_attribute(self, 'use_subscription_manager', 1, config, int)
        ##
        # @fixme HACK to work around too much voodoo to fix right now.
        self.__function_attribute = self.function
        set_attribute(self,'conversion',as_magnitude,config,_function)
        self.original_function = self.function
        if type(self.function) == types.StringType:
            self.function = string.replace(
                self.function, 'self.',
                'as_internal_node("%s").' % as_node_url(self)
                )
        set_attribute(self,'args','()',config)
        # fix for bad configuration
        if self.args == '':
            self.args = '()'
        self.__function_config = self.function
        self._last_time = None
        self._last_value = None
        self._period = self.parent.parent.period

    def start(self):
        Column.start(self)
        if (type(self.__function_config) == types.StringType and 
            string.count(self.__function_config,'as_node') == 1 and 
            self.__function_config.endswith('get')):
            func = self.__function_config
            self.__node = as_node(func[func.find('(')+2:func.rfind(')')-1])
            if self.use_subscription_manager:
                self._sid = SM.create_delivered(self, {1:as_node_url(self.__node)})
                self.function = self.get_last
            else:
                self.function = getattr(self.__node,func[func.rfind('.')+1:])
        rexec = self.parent.parent.get_environment()
        self.original_function = RFunction(self.function, args=self.args,
                                           context=self.context,
                                           rexec=rexec)
        self.function = self._convert
        self.variables = {}
        nodes = self.children_nodes()
        for potential_calculator in nodes:
            if hasattr(potential_calculator, 'evaluate'):
                if self._calculator: #oops
                    raise EAttributeError('Too many calculator nodes', self)
                self._calculator = potential_calculator
                self.function = self._evaluate # hook the calculator in
        self.__original_function = self.original_function
        self.original_function = self.__evaluate_original_function
        self.__started = 1
    def stop(self):
        self.__started = 0
        Column.stop(self)
        self.variables = None
        self._calculator = None
        if self._sid:
            SM.destroy(self._sid)
            self._sid = None
    def __evaluate_original_function(self):
        if not self.__started:
            msglog.log('broadway',msglog.types.WARN,
                       'Attempting to get value of '
                       'unstarted Column.  Will attempt start.')
            try:
                self.start()
            except:
                self.stop()
                raise
            msglog.log('broadway',msglog.types.INFO,'Column Start succeeded')
        elif self.__node is not None and self.__node.parent is None:
            self.__lock.acquire()
            try:
                # Redoing parent test with Lock acquired.  
                #   Prevents unecessary locking.
                if self.__node.parent is None:
                    msglog.log('broadway',msglog.types.WARN,
                               'Source node for Column %s has no parent' % self.name)
                    msglog.log('broadway',msglog.types.WARN,'Stopping Column %s' % self.name)
                    self.stop()
                    msglog.log('broadway',msglog.types.WARN,'Restarting Column %s' % self.name)
                    self.start()
            finally:
                self.__lock.release()
        return self.__original_function()
    def attach_variable(self, name): #defaults for self.get and calculator.get
        if   name == 'now':
            return time.time
        elif name == 'value':
            return self._current_value_
        elif name == 'last_value':
            return self._last_value_
        elif name == 'last_time':
            return self._last_time_
        elif name == 'period':
            return self._period_
        else:
            if debug: print 'Bad Attach:  Attempted to attach to "%s".' % name
            return self._bad_attach_
    def _current_value_(self):
        return self._convert()
    def _last_value_(self):
        if debug: print 'Get last value of :', self._last_value
        return self._last_value
    def _last_time_(self):
        if debug: print 'Get last time of :', self._last_time
        return self._last_time
    def _period_(self):
        if debug: print 'Get period : ' , self._period
        return self._period
    def _bad_attach_(self):
       raise EAttributeError('attempt to attach to non-existant variable',
                             self)
    ##
    # our hook to replace the function attribute with a calculator
    def _evaluate(self):
        now = self.scheduled_time()
        value = self._current_value_()
        if debug: print 'Now :', now, value
        answer = self._calculator.evaluate({'now':now, 'value':value})
        if debug: print 'Lasts :', now, value
        self._last_time = now
        self._last_value = value
        return answer
    ##
    # Hook for getting scheduled time from a periodic_column.
    # Mostly here for backwards-compatibility, function should
    # be self.parent.scheduled_time.
    #
    # @return Timestamp of current run.
    #
    def scheduled_time(self):
        if self.parent is None:
            return time.time()
        return self.parent.parent.scheduled_time()
    ##
    # @author Craig Warren
    # @return dictionary
    #   the current configuration dictionary
    #
    def configuration(self):
        config = Column.configuration(self)
        get_attribute(self,'context',config)
        get_attribute(self,'conversion',config,_name)
        config['function'] = self.__function_attribute
        get_attribute(self,'args',config)
        return config
    def _convert(self):
        return self.conversion(self.original_function())
    
    def get(self, skipCache=0): #async get from nodebrowser
        if self._calculator:
            return self._calculator.get()
        if not callable(self.function):
            raise ENotStarted('Function not callable, usually ' +
                              'means get called before start')
        return self._convert()
    def change_of_value(self, event):
        self._present_value = event.results()[1]['value']
    def get_last(self):
        if isinstance(self._present_value, Exception):
            raise self._present_value
        if not self._present_value:
            self._present_value = self.__node.get()
        return self._present_value
    def get_source_node_url(self):
        # HACK to get the source node URL
        if type(self.function) == types.StringType:
            return self.function.split('"')[1]
        return 'Unknown URL'
##
# @author Craig Warren
# @return periodiccolumn
#  returns and instanciated PeriodicColumn
#
def factory():
    return PeriodicColumn()
