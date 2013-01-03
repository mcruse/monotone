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
from math import *
import datetime
import random
import string
import time

from _translator import Translator

from mpx.lib import msglog
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute
from mpx.lib.exceptions import ECircularReference
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENotStarted
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_internal_node
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import is_node
from mpx.lib.node import is_node_url
from mpx.lib.utils import interpolate

from threading import Lock
from threading import _get_ident as thread_id

debug_default = 0
_module_lock = Lock()

def _as_node_get(url):
    node = as_node(url)
    return node.get

class Evaluator(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self._conversions = [self._as_node, self._attach_variable, self._as_is]
        self._threads = set()
        self.started = 0
        self._exception = None
        self.debug = debug_default
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
    def _as_node(self,reference):
        if reference in (None,'',u''):
            raise EInvalidValue('reference',reference,
                                'expected node reference')
        if reference == '$PARENT$':
            reference = '..'
        node = self.as_node(reference)
        if self.as_internal_node(reference) is self:
            raise ECircularReference(reference,self.name)
        return node.get
    def _as_is(self,value):
        return value
    def _attach_variable(self,name):
        return self.parent.attach_variable(name[1:])
    def start(self):
        CompositeNode.start(self)
        self.local_context = {}
        try:
            self.compiled_statement = compile(self.statement, '', 'eval')
            #examine each variable and decide what to do with it
            for variable in self.variables:
                name = variable['vn']
                definition = variable['node_reference']
                if self.local_context.has_key(name):
                    raise EInvalidValue('variable',name,
                                        'Variable name duplicated')
                exceptions = []
                conversions = self._conversions[:]
                while conversions:
                    conversion = conversions.pop(0)
                    try:
                        reference = conversion(definition)
                        break
                    except Exception,e:
                        exceptions.append(e)
                else:
                    self.local_context = {}
                    raise EInvalidValue('variable',name,
                                        ('Conversions %s Gave Errors %s.' %
                                         (self._conversions,exceptions)))
                self.local_context[name] = reference
            self.started = 1
        except Exception,e:
            self.started = 0
            self._exception = e
            raise
        return
    def get(self, skipCache=0):
        if self.started == 0:
            self.start()
        return self.evaluate(self.local_context)
    ##
    # Evaluate the expression with an optional context.  This can be used
    # to simulate a get(), using different variable bindings.
    #
    # @param context A dictionary of variable names and their values.
    # @default None If no <code>context</code> is provided, then
    #          the evaluator's configured context is used.
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
            context.update(local_context)
        values = self._get_values(local_context)
        return self._evaluate(values)
    def _get_values(self, context):
        _module_lock.acquire()
        try:
            local_context = {}
            id = thread_id()
            if id in self._threads:
                #if we don't remove it, this may become permanent
                self._threads.remove(id)
                raise ECircularReference('Recursion detected', self.name)
            self._threads.add(id)
        finally:
            _module_lock.release()
        try:
            for k in context.iterkeys():
                v = context[k]
                local_context[k] = v() if callable(v) else v
        finally:
            _module_lock.acquire()
            try:
                self._threads.discard(id)
            finally:
                _module_lock.release()
        return local_context
    def _evaluate(self, value_map):
        answer = eval(self.compiled_statement, globals(), value_map)
        return answer

class Converter(Evaluator):
    def configure(self,cd):
        tmpcd=dict(cd)
        value=tmpcd.pop('value')
        statement=tmpcd.pop('statement')
        tmpcd['variables'] = [{'vn':'value','node_reference':value},]
        tmpcd['statement'] = statement
        Evaluator.configure(self,tmpcd)
        return
    def configuration(self):
        cd=Evaluator.configuration(self)
        variables=cd.pop('variables')
        cd['value'] = variables['node_reference']
        return tmpcd
