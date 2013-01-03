"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import bisect
import threading
from utilities import locked_method

def entrycmp(entry1, entry2):
    comparison = entry1.runswhen() - entry2.runswhen()
    if comparison < 0:
        return -1
    elif comparison == 0:
        return 0
    else:
        return 1

class Collection(object):
    """
        Data structure which maintains two syncrhonized lists.  
        One list is a list of entry run times (using uptime), and 
        the other is list of entries themselves.  Both lists are 
        kept in sorted order at all times, whith the smallest 
        run-time and corresponding entry at index 0, and increasing 
        run-time / entries going up the list.
        
        Structure may be initialized from unsorted list of 
        entries.
    """
    def __init__(self, entries=()):
        super(Collection, self).__init__()
        self._entries = list(entries)
        self._runtimes = []
        self.rebuild()
    def isempty(self):
        return not self._entries
    def getentries(self):
        return list(self._entries)
    def getruntimes(self):
        return list(self._runtimes)
    def addentry(self, entry):
        return self._addentry(entry)
    def addentries(self, entries):
        return map(self._addentry, entries)
    def removeentry(self, entry):
        return self._removeentry(entry)
    def removeentries(self, entries):
        return map(self._removeentry, entries)
    def nextruntime(self):
        if not self._runtimes:
            return None
        return self._runtimes[0]
    def lastruntime(self):
        if not self._runtimes:
            return None
        return self._runtimes[-1]
    def nextentry(self):
        if not self._entries:
            return None
        return self._entries[0]
    def lastentry(self):
        if not self._entries:
            return None
        return self._entries[-1]
    def popentry(self, runtime = 0):
        index = bisect.bisect_left(self._runtimes, runtime)
        if runtime and self._runtimes[index: index +1] != [runtime]:
            raise IndexError('Entry runtime not in collection.')
        return self._popindex(index)
    def popentries(self, runtime):
        index = bisect.bisect_right(self._runtimes, runtime)
        return self._popcount(index)
    def _addentry(self, entry):
        runtime = entry.runswhen()
        if len(self._runtimes):
            index = bisect.bisect_right(self._runtimes, runtime)
        else:
            index = 0
        self._entries.insert(index, entry)
        self._runtimes.insert(index, runtime)
        return index
    def _removeentry(self, entry):
        runtime = entry.runswhen()
        if len(self._runtimes) > 3:
            index = bisect.bisect_left(self._runtimes, runtime)
        else:
            index = 0
        while index < len(self._entries):
            if self._entries[index] is entry:
                break
            index = index + 1
        else:
            raise IndexError('Entry not in collection.')
        del(self._entries[index])
        del(self._runtimes[index])
        return index
    def _popcount(self, count):
        entries = self._entries[0:count]
        del(self._runtimes[0:count])
        del(self._entries[0:count])
        return entries
    def _popindex(self, index):
        runtime = self._runtimes.pop(index)
        return self._entries.pop(index)
    def __getitem__(self, *args):
        return self._entries.__getitem__(*args)
    def __getslice__(self, *args):
        return self._entries.__getslice__(*args)
    def __len__(self):
        return len(self._entries)
    length = property(__len__)
    def validate(self):
        entries = list(self._entries)
        runtimes = list(self._runtimes)
        assert len(runtimes) == len(entries)
        assert runtimes == [entry.runswhen() for entry in entries]
    def rebuild(self):
        entries = list(self._entries)
        if entries:
            entrypairs = [(entry.runswhen(),entry) for entry in self._entries]
            entrypairs.sort()
            runtimes,entries = zip(*entrypairs)
            self._entries = list(entries)
            self._runtimes = list(runtimes)
    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self._entries)
    def __str__(self):
        entries = ', '.join(['"%s"' % entry for entry in self._entries])
        return '%s(%s)' % (type(self).__name__, entries)

class SynchronizedCollection(Collection):
    def __init__(self, *args):
        self._changelock = threading.Lock()
        super(SynchronizedCollection, self).__init__(*args)
    def get_lock(self):
        return self._changelock
    addentry = locked_method(get_lock, Collection.addentry)
    addentries = locked_method(get_lock, Collection.addentries)
    removeentry = locked_method(get_lock, Collection.removeentry)
    removeentries = locked_method(get_lock, Collection.removeentries)
    popentry = locked_method(get_lock, Collection.popentry)
    popentries = locked_method(get_lock, Collection.popentries)

class Flag(object):
    """
        Small simple object which mimics exposes an 
        interfaces similar to threading.Event instances.
        The difference betweeen a Flag and Event is that 
        Flag instances are lighter wait and do not 'wait'.
        
        Second major difference is that Flag class provides 
        '__call__' method which is alias for 'isSet'; this makes 
        Flag instances callable to test value as well.
        
        When a flag is used as an attribute on an object, users 
        of the object may invoke the flag just as they would 
        a test method implemented on the object itself.  
    """
    __slots__ = ('_value')
    def __init__(self, initvalue = False):
        self._value = bool(initvalue)
    def set(self):
        self._value = True
    def clear(self):
        self._value = False
    def isSet(self):
        return self._value
    def __call__(self):
        return self.isSet()
    def __str__(self):
        classname = type(self).__name__
        return '%s(%s)' % (classname, self.isSet())
    def __repr__(self):
        return '<%s at %#x>' % (self, id(self))

class Counter(object):
    def __init__ (self, initial_value=0):
        self._initvalue = initial_value
        self.setvalue(initial_value)
    def increment (self, delta = 1):
        current = self.getvalue()
        self.setvalue(current + delta)
        return current
    def decrement(self, delta = 1):
        current = self.getvalue()
        self.setvalue(current - delta)
        return current
    def getvalue(self):
        return self._value
    def setvalue(self, value):
        self._value = long(value)
    def reset(self):
        self.setvalue(self._initvalue)
    def __nonzero__ (self):
        return self.getvalue() != 0
    def __str__ (self):
        return 'Counter(%s)' % self.getvalue()
    def __repr__ (self):
        return '<Counter value=%s at %x>' % (self.getvalue(), id(self))

class LockedFlag(Flag):
    """
        Extends Flag class and transparently adds locking 
        around methods getting and setting flag state.  The 
        only reason to use this type over a normal threading.Event, 
        since some of the lightweightness is sacrificed to using 
        a Lock instance, is that this class allows a lock to be 
        passed in so that a single shared lock may be used for 
        multipl LockedFlag instances.
    """
    __slots__ = ('_statelock')
    def __init__(self, lock = None, *args):
        if lock is None:
            lock = threading.Lock()
        self._statelock = lock
        super(LockedFlag, self).__init__(*args)
    def getlock(self):
        return self._statelock
    set = locked_method(getlock, Flag.set)
    isSet = locked_method(getlock, Flag.isSet)
    clear = locked_method(getlock, Flag.clear)

class NamedFlag(Flag):
    """
        Simple extension of Flag class which allows name 
        to be associated with flag instances.  The primary 
        benefit of provided by this type over normal Flag 
        types is the support of __str__ and __repr__ methods 
        which use the name to return meaningful strings.
    """
    __slots__ = ('_name')
    def __init__(self, name, *args):
        self._name = name
        super(NamedFlag, self).__init__(*args)
    def getName(self):
        return self._name
    def __str__(self):
        classname = type(self).__name__
        return '%s("%s" is %s)' % (classname, self.getName(), self.isSet())
