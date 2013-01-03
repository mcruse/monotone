"""
Copyright (C) 2002 2003 2006 2007 2008 2010 2011 Cisco Systems

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
import sys
from mpx.lib.node import CompositeNode, as_node, as_node_url, is_node, \
     as_internal_node, is_node_url
from _translator import Translator
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.exceptions import EInvalidValue, ECircularReference, ENotStarted
from threading import _get_ident as thread_id
from threading import Lock
from math import *
import random
from mpx.lib import msglog
from mpx.lib.utils import interpolate
import time, string
#import datetime #python 2.5 only

debug = 0
_module_lock = Lock()

def _as_node_get(url):
    node = as_node(url)
    return node.get

class Calculator(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self._threads = set()
        self.started = 0
        self._failed = {}
        self._exception = None
        return
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'statement', '', cd, str)
        set_attribute(self, 'variables', [], cd)
        return
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'statement', cd, str)
        get_attribute(self, 'variables', cd)
        return cd
    def as_input_node(self, reference):
        if reference in (None,'',u''):
            raise EInvalidValue('reference', reference, 'expected node URL')
        if reference == '$PARENT$':
            reference = '..'
        node = self.as_node(reference)
        if self.as_internal_node(reference) is self:
            raise ECircularReference(reference,self.name)
        return node
    def as_node_input(self, name, node):
        return node.get
    def _attach_variable(self,name):
        return self.parent.attach_variable(name[1:])
    def define_input(self, name, definition):
        resolved = True
        exceptions = []
        try:
            value = float(definition)
        except Exception,error:
            exceptions.append(sys.exc_info())
            try:
                node = self.as_input_node(definition)
            except Exception,error:
                exceptions.append(sys.exc_info())
                try:
                    value = self._attach_variable(definition)
                except:
                    resolved = False
                    exceptions.append(sys.exc_info())
            else:
                value = self.as_node_input(name, node)
        else:
            if isinstance(definition, str):
                # Attempt integer conversion because float worked.
                try:
                    value = int(definition)
                except ValueError:
                    pass    
        if not resolved:
            # Log input resolution for definition once.
            if self._failed.get(name) != definition:
                message = "%s cannot resolve %r: %r.  Exceptions follow."
                msglog.warn(message % (self, name, definition))
                while exceptions:
                    error = exceptions.pop()
                    msglog.exception(prefix="handled", exc_info=error)
            self._failed[name] = definition
            raise ValueError("Unable to resolve definition: %r" % definition)
        else:
            self._failed.pop(name, None)
        return value
    def setup_context(self):
        context = {}
        for variable in self.variables:
            name = variable['vn']
            definition = variable['node_reference']
            if context.has_key(name):
                raise EInvalidValue('variable', name, 'Duplicate name')
            context[name] = self.define_input(name, definition)
        return context
    def start(self):
        result = super(Calculator, self).start()
        try:
            self.compiled_statement = compile(self.statement, '', 'eval')
            self.local_context = self.setup_context()
            self.started = 1
        except Exception,e:
            self.started = 0
            self._exception = e
            self.local_context = {}
            raise
        return result
    def stop(self):
        result = super(Calculator, self).stop()
        self.started = 0
        self.local_context = {}
        self.compiled_statement = None
        return result
    def get(self, skipCache=0):
        if debug: 
            print 'Calculator get', self
        if not self.is_running():
            raise ENotStarted(self)
        if not self.started:
            self.start()
        return self.evaluate(self.local_context)
    ##
    # Evaluate the expression with an optional context.  This can be used
    # to simulate a get(), using different variable bindings.
    #
    # @param context A dictionary of variable names and their values.
    # @default None If no <code>context</code> is provided, then
    #          the calculators configured context is used.
    # @note If <code>context</code> is not None and is not the same as
    # the configured context, then a temporary "local_context" is created
    # which is a copy of the configured context, update with
    # <code>context</code>.
    def evaluate(self, context=None):
        if context is None:
            context = self.local_context
        local_context = context
        if not (local_context is self.local_context):
            local_context = self.local_context.copy()
            local_context.update(context)
            # Note modification to provided context--bad form.
            context.update(local_context)            
        values = self._get_values(local_context)
        return self._evaluate(values)
    def _get_values(self, context):
        if debug: print 'Calculator evaluate', self, context
        _module_lock.acquire()
        try:
            local_context = {}
            id = thread_id()
            if id in self._threads:
                self._threads.remove(id) #if we don't remove it, this may become permanent
                raise ECircularReference('Recursion detected', self.name)
            self._threads.add(id)
        finally:
            _module_lock.release()
        try:
            for k in context.iterkeys():
                v = context[k]
                if debug: print 'Calculator key/value: ',k, v
                if callable(v): #node gets and forced variables
                    x = v()
                    if not hasattr(x,'__abs__'):
                        if hasattr(x,'__float__'):
                            x = float(x)
                        elif hasattr(x,'__int__'):
                            x = int(x)
                    local_context[k] = x
                    if debug: print 'Callable returned :', local_context[k]
                else:
                    local_context[k] = v
        finally:
            _module_lock.acquire()
            try:
                self._threads.discard(id)
            finally:
                _module_lock.release()
        return local_context
    def _evaluate(self, value_map):
        if debug: print 'Calculator enter _evaluate'
        try:
            if debug: print 'Calculator try eval...'
            answer = eval(self.compiled_statement, globals(), value_map)
            if debug: print 'Calculator Answer: ', str(answer)
        except:
            if debug: print 'Calculator failed to eval'
            answer = None
        return answer

class PeriodicAverageColumn(Calculator):
    def configure(self,cd):
        cd['statement'] = '(value - last_value)/(now - last_time)'
        cd['variables'] = [{'vn':'value','node_reference':'$value'},
                           {'vn':'last_value','node_reference':'$last_value'},
                           {'vn':'last_time','node_reference':'$last_time'},
                           {'vn':'period','node_reference':'$period'},
                           {'vn':'now','node_reference':'$now'}]
        Calculator.configure(self,cd)
class PeriodicDeltaColumn(Calculator):
    def configure(self,cd):
        cd['statement'] = 'value - last_value'
        cd['variables'] = [{'vn':'value','node_reference':'$value'}, 
                           {'vn':'last_value','node_reference':'$last_value'}]
        Calculator.configure(self,cd)
        
        
