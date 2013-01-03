"""
Copyright (C) 2005 2010 2011 Cisco Systems

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
import string
import inspect
from mpx.lib import msglog

OFF = 0

class ArgumentBinder:
        def __init__(self,callable,prepend=(),append=(),**keywords):
            self._callable = callable
            self._prepend = prepend
            self._append = append
            self._keywords = keywords
        def __call__(self,*args,**keywords):
            keywords.update(self._keywords)
            return self._callable(*(self._prepend + args + self._append),**keywords)

class _CallHooker:
    _hooker_class = None
    _wrapped_class = None
    _targets = None
    _excluded = []
    _target_description = None
    __excluded = ['__class__','_CallHooker__wrap',
                  'execute_function','_hooker_class',
                  '_targets','__init__', '_target_description']
    def __init__(self,*args,**keywords):
        if self._targets is None: self._targets = dir(self)
        if self._target_description is None:
            name = self._wrapped_class.__name__
            self._target_description = '(%s) %s' % (id(self),name)
        if hasattr(self._wrapped_class,'__init__'):
            self.execute_function('__init__',
                self._wrapped_class.__init__,self,*args,**keywords)
        self.__wrap(self._targets,self.__excluded + self._excluded)
    def __wrap(self,targets=[],excluded=[]):
        for name in targets:
            attribute = getattr(self,name)
            if name in excluded or attribute in excluded: continue
            if isinstance(attribute,ArgumentBinder): continue
            if inspect.isclass(attribute): continue
            if not callable(attribute): continue
            bound = ArgumentBinder(self.execute_function,(name,attribute))
            setattr(self,name,bound)
    def execute_function(self,name,function,*args,**keywords):
        description = (self._target_description + '.%s%s' % (name,args))[:50]
        return function(*args,**keywords)
    def __repr__(self):
        response = '_CallHooker(%s)'
        try: response = response % self._wrapped_class.__repr__(self)
        except AttributeError: 
            response = response % self._wrapped_class.__name__
        return reponse
    def __str__(self):
        response = '_CallHooker(%s)'
        try: response = response % self._wrapped_class.__str__(self)
        except AttributeError: 
            response = response % self._wrapped_class.__name__
        return response

class Counter:
    def __init__(self):
        self.__count = 0
    def increment(self):
        count = self.__count
        self.__count += 1
        return count
class _ProfilingHooker(_CallHooker):
    def __init__(self,printing,*args,**keywords):
        self.__counter = Counter()
        self.__print = True
        self.__compact = printing == 'compact'
        self._excluded = dir(_ProfilingHooker)
        _CallHooker.__init__(self,*args,**keywords)
    def execute_function(self,name,function,*args,**keywords):
        count = self.__counter.increment()
        description = self._target_description + '.%s' % name
        if not self.__compact:
            try: description += ('%s' % (args,))
            except: pass
        if len(description) > 75: description = description[0:72] + '...'
        self.__output('[%s] Start %s' % (count,description))
        t_start = time.time()
        result = function(*args,**keywords)
        t_end = time.time()
        t_delta = t_end - t_start
        profile = ['[%s] Finish %s:','%s(%s) to %s(%s)]','Time Lapse: %s']
        profile = string.join(profile,'\n\t')
        profile = profile % (count,description,time.ctime(t_start),
                              t_start,time.ctime(t_end),t_end,t_delta)
        self.__output(profile)
        return result
    def off(self):
        self.__print = 0
    def on(self):
        self.__print = 1
    def __output(self,message):
        if self.__print and not OFF: print message
    def __repr__(self):
        response = '_ProfilingHooker(%s)'
        try: response = response % self._wrapped_class.__repr__(self)
        except AttributeError: 
            response = response % self._wrapped_class.__name__
        return response
    def __str__(self):
        response = '_ProfilingHooker(%s)'
        try: response = response % self._wrapped_class.__str__(self)
        except AttributeError: 
            response = response % self._wrapped_class.__name__
        return response

def Profiled(class_object,recreate=1,targets=None,printing='pretty'):
    action = '%%sProfiling %r.  %%s, targets: %s' % (class_object,targets)
    if not recreate:
        return class_object
    if not inspect.isclass(class_object):
        print action % ('Not ', 'Not class defnition')
        return class_object
    if issubclass(class_object,_CallHooker):
        print action % ('Not ','Already _CallHooker subclass')
        return class_object
    if issubclass(class_object,ArgumentBinder):
        print action % ('Not ', 'Is ArgumentBinder subclass')
        raise Exception('Unexpected behaviour.  Please document.')
    print action % ('','')
    class HookerMaker(class_object,_ProfilingHooker):
        _hooker_class = _ProfilingHooker
        _wrapped_class = class_object
        _targets = targets
        def __init__(self,*args,**keywords):
            return _ProfilingHooker.__init__(self,printing,*args,**keywords)
    return HookerMaker
