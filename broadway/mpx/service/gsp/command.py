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
from mpx.lib import msglog
from mpx.lib import ReloadableSingletonFactory
from mpx.lib.exceptions import ENotFound
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import EAbstract
from mpx.lib.node import as_node
from mpx.lib.uuid import UUID
from mpx.lib.thread_pool import ThreadPool
from datatypes import *

class Cache(dict):
    """
    A class used to provide a fixed size dictionary
    """
    def __init__(self, size=20):
        dict.__init__(self)
        self._maxsize = size
        self._stack = []

    def __setitem__(self, name, value):
        if len(self._stack) >= self._maxsize:
            self.__delitem__(self._stack[0])
            del self._stack[0]
        self._stack.append(name)
        return dict.__setitem__(self, name, value)

class CommandManager(object):
    def __init__(self):
        super(CommandManager, self).__init__()
        self._worker_thread = ThreadPool(
            2, name='GlobalSetpointManager-ThreadPool'
            )
        self._transactions = Cache(size=20)
        
    def enqueue(self, command_set):
        self._transactions[command_set.tid] = command_set
        self._worker_thread.queue_noresult(command_set)
        
    def get_push_values_progress(self, transaction_id):
        try:
            return self._transactions[transaction_id].get_status()
        except KeyError:
            raise ENotFound()
        
    def singleton_unload_hook(self):
        pass
    
COMMAND_MANAGER = ReloadableSingletonFactory(CommandManager)
        
class CommandSet(object):
    def __init__(self, commands, operation='execute'):
        self.tid = UUID()
        self._commands = []
        for cmd in commands:
            if isinstance(cmd, CommandIface):
                self._commands.append(cmd)
        self._completed = 0
        self._num_commands = len(self._commands)
        self._errors = 0
        self._operation = operation
        value_map = {
            'completed':False, 'success':False, 'report_items':[],
            'transaction_id':self.tid, 'percent_complete':0         
            }
        self._status = TransactionStatus(value_map)
        super(CommandSet, self).__init__()
        
    def execute(self, *args):
        self._apply('execute', *args)
                
    def undo(self, *args):
        self._apply('undo', *args)
        
    def _apply(self, operation, *args):
        for cmd in self._commands:
            self._completed += 1
            try:
                getattr(cmd, operation)(*args)
            except Exception, e:
                self._errors += 1
                if isinstance(e, ENoSuchName):
                    severity = 'Error'
                else:
                    severity = 'Warning'
                description = str(e)
                custom = {} # reserved for future use, see "Global Setpoints SFS"
                value_map = {
                    'severity':severity, 
                    'description':description,
                    'custom':custom
                    }
                self._status.report_items.append(ErrorReport(value_map))
                cmd.failure(*args)
          
    def get_transaction_id(self):
        return self.tid
          
    def get_status(self):
        if self._status.completed == False:
            if self._completed == self._num_commands:
                self._status.completed = True
                if self._errors == 0:
                    self._status.success = True
            try:
                self._status.percent_complete = \
                    int((float(self._completed) / float(self._num_commands)) * 100)
            except ZeroDivisionError:
                self._status.percent_complete = 0
        return self._status 
        
    def __call__(self, *args):
        getattr(self, self._operation)(*args)
##
# The command interface - to be implemented by subclass    
class CommandIface(object):
    def execute(self, *args): raise EAbstract()
    def failure(self, *args): raise EAbstract()
    def undo(self, *args): raise EAbstract()
    
class SetCommand(CommandIface):
    class Unknown(object): pass
    def __init__(self, target, value):
        self._target = target
        self._value = value
        self._last_value = self.Unknown()
        super(SetCommand, self).__init__()
        
    def execute(self, *args):
        target = as_node(self._target)
        try: self._last_value = target.get()
        # undo not possible on except
        except: pass
        target.set(self._value)
        
    def failure(self, *args):
        message = 'Failed to write %s to %s' % (self._value, self._target)
        msglog.log('Global Setpoint Manager', msglog.types.WARN, message)
        msglog.exception()
    
    def undo(self, *args):
        if not isinstance(self._last_value, self.Unknown):
            as_node(self._target).set(self._last_value)
            
class OverrideCommand(SetCommand):
    def __init__(self, target, value, priority_level=16):
        super(OverrideCommand, self).__init__(target, value)
        self._priority_level = priority_level
        
    def execute(self, *args):
        target = as_node(self._target)
        try: self._last_value = target.get_override_at(self._priority_level)
        # undo not possible
        except: pass
        target.override(self._value, self._priority_level)

    def undo(self, *args):
        if not isinstance(self._last_value, self.Unknown):
            as_node(self._target).override(
                self._last_value, self._priority_level
                )
            
class ReleaseCommand(CommandIface):
    class Unknown(object): pass
    def __init__(self, target, priority_level=16):
        self._target = target
        self._priority_level = priority_level
        self._last_value = self.Unknown()
        super(ReleaseCommand, self).__init__()
        
    def execute(self, *args):
        target = as_node(self._target)
        try:
			self._last_value = target.get_override_at(self._priority_level)
			target.release(self._priority_level)
			# undo not possible
        except: pass
        
        
    def failure(self, *args):
        message = 'Failed to release priority level: %s override on %s' % \
            (self._priority_level, self._target)
        msglog.log('Global Setpoint Manager', msglog.types.WARN, message)
        msglog.exception()
        
    def undo(self, *args):
        if not isinstance(self._last_value, self.Unknown):
            as_node(self._target).override(
                self._last_value, self._priority_level
                )
            
