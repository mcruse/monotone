"""
Copyright (C) 2003 2004 2006 2009 2010 2011 Cisco Systems

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
from exceptions import ENotImplemented as _ENotImplemented
from threading import RLock as _RLock
from exceptions import MpxException as _MpxException

class EReloadableSingleton(_MpxException):
    pass

class ELoadingDisabled(EReloadableSingleton):
    pass

class ReloadableSingletonInterface(object):
    ##
    # Classes that support being instanciated as ReloadableSingleton's MUST
    # implement this method.  It is called immediately before the singleton is
    # dereferrenced by the facade.
    # @note I'm not sure why this is mandatory.
    # @note There is some possiblitly of race conditions occurring,
    #       but the intent is for use during system shutdowns, running upgrades
    #       and test frameworks...
    def singleton_unload_hook(self):
        raise _ENotImplemented

class _ReloadableSingleton(object):
    __facades = []
    __lock = _RLock()
    def __getattr__(self, name):
        if self.__instance is None:
            self.__lock.acquire()
            try:
                self.__realize()
            finally:
                self.__lock.release()
        result = getattr(self.__instance, name)
        return result
    def __setattr__(self, name, value):
        if self.__instance is None:
            self.__lock.acquire()
            try:
                self.__realize()
            finally:
                self.__lock.release()
        return setattr(self.__instance, name, value)
    def __setitem__(self,name,value):
        if self.__instance is None:
            self.__lock.acquire()
            try:
                self.__realize()
            finally:
                self.__lock.release()
        result = self.__instance.__setitem__(name, value)
        return result
    def __getitem__(self,name):
        if self.__instance is None:
            self.__lock.acquire()
            try:
                self.__realize()
            finally:
                self.__lock.release()
        result = self.__instance.__getitem__(name)
        return result
    def __init__(self, klass, *args, **keywords):
        self.__dict__['_ReloadableSingleton__klass'] = klass
        self.__dict__['_ReloadableSingleton__args'] = args
        self.__dict__['_ReloadableSingleton__keywords'] = keywords
        self.__dict__['_ReloadableSingleton__instance'] = None
        self.__dict__['_ReloadableSingleton__loadable'] = True
        self.__lock.acquire()
        try:
            self.__facades.append(self)
        finally:
            self.__lock.release()
        return
    def __str__(self):
        return str(self.__instance)
    def __repr__(self):
        return repr(self.__instance)
    def __realize(self):
        if not self.__instance is None:
            return
        if not self.__loadable:
            raise ELoadingDisabled("Instance currently not loadable.")
        instance = self.__klass(*self.__args,**self.__keywords)
        assert hasattr(instance, 'singleton_unload_hook'), (
            "ReloadableSingletonInterface requires a singleton_unload_hook"
            " method."
            )
        self.__dict__['_ReloadableSingleton__instance'] = instance
        return
    def __unrealize(self):
        if self in self.__facades:
            if not self.__instance is None:
                self.__instance.singleton_unload_hook()
                self.__dict__['_ReloadableSingleton__instance'] = None
        return
    ##
    # Realize an actual instance of this singleton.  If the instance is already
    # realized, then do nothing.
    def singleton_load(self):
        self.__lock.acquire()
        try:
            self.__realize()
        finally:
            self.__lock.release()
        return
    ##
    # Force the underlying instance of the singleton to be unrealized.  If the
    # instance is already  unrealized, then do nothing.
    def singleton_unload(self):
        self.__lock.acquire()
        try:
            self.__unrealize()
        finally:
            self.__lock.release()
        return
    ##
    # Set the loadable state of a singleton.  This state stays in effect until
    # changed by a subsequent call.  This does not change the whether or not
    # the instance is actually already loaded not access to the actual instance
    # if it is loaded.
    #
    # @param loadable Boolean indicating whether to allow loading of the actual
    #                 instance of a singleton's facade.
    def singleton_set_loadable_state(self, loadable):
        self.__lock.acquire()
        try:
            was_loadable = self.__loadable
            self.__dict__['_ReloadableSingleton__loadable'] = loadable
        finally:
            self.__lock.release()
        return was_loadable
    ##
    # Class method that will search for a specific facade and unrealize its
    # actual instance.
    #
    # @param instance_facade The facade to the actual instance to unload.
    def singleton_unload_by_facade(klass, instance_facade):
        klass.__lock.acquire()
        try:
            facades = []
            facades.extend(klass.__facades)
            for facade in facades:
                if facade is instance_facade:
                    facade.__unrealize()
                    return 1
        finally:
            klass.__lock.release()
        return 0
    singleton_unload_by_facade = classmethod(singleton_unload_by_facade)
    ##
    # Class method that will search for a specific instance in the list of all
    # singleton facades and unrealize it.
    #
    # @param actual_instance The underlying instance to a singleton facade.
    # @note Typically, only an underlying instance would use this.  And it's
    #       a bit of a hack - too much coupling.
    def singleton_unload_by_instance(klass, actual_instance):
        klass.__lock.acquire()
        try:
            facades = []
            facades.extend(klass.__facades)
            for facade in facades:
                if facade.__instance is actual_instance:
                    facade.__unrealize()
                    return 1
        finally:
            klass.__lock.release()
        return 0
    singleton_unload_by_instance = classmethod(singleton_unload_by_instance)
    ##
    # Class method that will unload all singleton's underlying actual
    # instances. 
    def singleton_unload_all(klass):
        klass.__lock.acquire()
        try:
            facades = []
            facades.extend(klass.__facades)
            for facade in facades:
                facade.__unrealize()
        finally:
            klass.__lock.release()
        return
    singleton_unload_all = classmethod(singleton_unload_all)
    ##
    # Class method that will apply a LOADABLE state to all currently existing
    # singletons.  This does not change the whether or not
    # the instance is actually already loaded not access to the actual instance
    # if it is loaded.
    #
    # @param loadable Boolean indicating whether to allow loading of the actual
    #                 instances of the singletons' facades.
    def singleton_set_loadable_state_all(klass, loadable):
        klass.__lock.acquire()
        try:
            facades = []
            facades.extend(klass.__facades)
            for facade in facades:
                facade.singleton_set_loadable_state(loadable)
        finally:
            klass.__lock.release()
        return
    singleton_set_loadable_state_all = classmethod(
        singleton_set_loadable_state_all
        )
    import edtlib as _edtlib
    def _edt_encode(cls, rso):
        o = rso.__instance
        encoder = cls._edtlib.codec_map.lookup(o).encoder
        return encoder(o)
    _edt_encode = classmethod(_edt_encode)
    def _edt_register(cls):
        return cls._edtlib.register_class(
            cls, decoder=None, encoder=cls._edt_encode
            )
    _edt_register = classmethod(_edt_register)

_ReloadableSingleton._edt_register() # Register an Elemental Data Type encoder.

def ReloadableSingletonFactory(klass, *args, **keywords):
    return _ReloadableSingleton(klass, *args, **keywords)
