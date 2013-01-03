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
import sys
import array
import string
import time
import mpx.lib
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.node import CompositeNode
from mpx.lib.exceptions import ETimeout
from mpx.lib.threading import Lock

def _none(object):
    return object
_functions = {'float':float,
              'string':str,
              'integer':int,
              'none':_none,
              'None':_none,
              None:_none}
def _function(name):
    return _functions[name]
def _name(function):
    for name,func in _functions.items():
        if func == function:
            return str(name)
    raise KeyError(function)
class Quad4(CompositeNode):
    class _Cache:
        def __init__(self,life=30):
            self._life = 30
            self._updated = 0
            self._cache = {}
        def life(self,life=None):
            if life is not None:
                self._life = life
            return self._life
        def expired(self):
            if time.time() - self._updated > self._life:
                return 1
            return 0
        def expires(self):
            return self._updated + self._life
        def renew(self):
            self._updated = time.time()
        def clear(self):
            for key in self._cache.keys():
                self._cache[key] = None
        def __getattr__(self,attr):
            return getattr(self._cache,attr)
    def __init__(self):
        self._cache = Quad4._Cache()
        self._cache_lock = Lock()
        CompositeNode.__init__(self)
    def configure(self, config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'id', 0, config, str)
        set_attribute(self,'cache_life',30,config,float)
        set_attribute(self,'timeout',10,config,float)
        set_attribute(self,'patience',1,config,float)
        self.port = self.parent
    def configuration(self):
        config = CompositeNode.configuration(self)
        config['port'] = config['parent']
        get_attribute(self, 'id', config)
        get_attribute(self,'cache_life',config,str)
        get_attribute(self,'timeout',config,str)
        get_attribute(self,'patience',config,str)
        return config
    def start(self):
        self._cache.life(self.cache_life)
        self.port.open()
        CompositeNode.start(self)
    def _add_child(self,child):
        if isinstance(child,Quad4Value):
            self._cache[child.id] = None
        CompositeNode._add_child(self,child)
    def _request_print(self):
        cmd = array.array('B',[2])
        id = '0'*(4-len(self.id[-4:])) + self.id[-4:]
        cmd.fromstring(id)
        self.port.drain()
        self.port.write(cmd)
        self.port.flush()
    def _readlines(self):
        lines = []
        timeout = self.timeout
        data = array.array('c')        
        try:
            while self.port.read_upto(data,('\n'),timeout):
                lines.append(data.tostring())
                del(data[:])
                timeout = self.patience
        except ETimeout:
            pass
        return lines
    def _refresh_cache(self,lines):
        self._cache.clear()
        for line in lines:
            id = line[0:line.find(' ')]
            if self._cache.has_key(id):
                self._cache[id] = line
        self._cache.renew()
    def get_line(self,id,skipCache):
        self._cache_lock.acquire()
        try:
            if skipCache or self._cache.expired() or self._cache[id] is None:
                self._request_print()
                lines = self._readlines()
                self._refresh_cache(lines)
        finally:
            self._cache_lock.release()
        return self._cache[id]
    
class Quad4Value(CompositeNode):
    def configure(self,config):
        set_attribute(self,'id',REQUIRED,config)
        set_attribute(self,'column',-2,config,int)
        set_attribute(self,'spaces',0,config,int)
        set_attribute(self,'conversion',float,config,_function)
        CompositeNode.configure(self,config)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self,'id',config)
        get_attribute(self,'column',config,str)
        get_attribute(self,'spaces',config,str)
        set_attribute(self,'conversion',float,config,_name)
        return config
    def get(self, skipCache=0):
        line = self.parent.get_line(self.id,skipCache)
        if line is None:
            raise ETimeout()
        list = string.split(line)
        if not self.spaces:
            value = list[self.column]
        elif self.column >= 0 or (self.column + self.spaces + 1) < 0:
            value = string.join(list[self.column:self.column+self.spaces+1])
        else:
            value = string.join(list[self.column:])
        return self.conversion(value)



