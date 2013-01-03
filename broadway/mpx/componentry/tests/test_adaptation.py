"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
from mpx.componentry import Interface
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry import query_multi_adapter

class IA(Interface):
    def show(name = 'shane'):
        """
            Print name 'name'.
        """


class IB(Interface):
    def show(name = 'shane'):
        """
            Print name 'name'.
        """


class IC(Interface):
    def show(name = 'shane'):
        """
            Print name 'name'.
        """



class INoA(Interface):
    def say(name = 'shane'):
        """
            Print name 'name'.
        """


class INoB(Interface):
    def say(name = 'shane'):
        """
            Print name 'name'.
        """


class INoC(Interface):
    def say(name = 'shane'):
        """
            Print name 'name'.
        """


class A(object):
    implements(IA)
    def show(self, name = 'shane'):
        print name


class A2(A):
    def show(self, name = 'shane'):
        print 'A2: ' + name


class NoIA(object):
    implements(INoA)
    def say(self, something):
        print something


class NoIA2(NoIA):
    def say(self, something):
        print 'NoIA2: ' + something


class NoIB(object):
    implements(INoB)
    def say(self, something):
        print 'NoIB: ' + something


class NoI(object):
    def say(self, something):
        print 'NoIB: ' + something


class AdaptsNone(object):
    implements(IC)
    adapts(None)
    def __init__(self, context):
        self.context = context
    def show(self, name = 'shane'):
        self.context.say(name)


register_adapter(AdaptsNone)
noi = NoI()
adaptednoi = IC(noi)
assert type(adaptednoi) is AdaptsNone, 'Got wrong Adapter!'



class Adapts(object):
    implements(IA)
    adapts(INoA)
    def __init__(self, context):
        self.context = context
    def show(self, name = 'shane'):
        self.context.say(name)

class AdaptsSubclass(Adapts):
    adapts(INoB)


register_adapter(Adapts)
register_adapter(AdaptsSubclass)
noia = NoIA()
adaptednoia = IA(noia)
assert type(adaptednoia) is Adapts, 'Got wrong Adapter!'
noib = NoIB()
adaptednoib = IA(noib)
assert type(adaptednoib) is AdaptsSubclass, 'Got wrong Adapter!'
assert Adapts.__used_for__ == [INoA], 'Adapts __used_for__ wrong!'
assert AdaptsSubclass.__used_for__ == [INoB], 'AdaptsSubclass __used_for__ wrong!'


class MultiAdapts(object):
    implements(IB)
    adapts(INoA, INoB)
    def __init__(self, a, b):
        self.contexts = [a, b]
    def show(self, name = 'shane'):
        for context in self.contexts:
            context.say(name)


register_adapter(MultiAdapts)
noia = NoIA()
noib = NoIB()
adapted = query_multi_adapter((noia, noib), IB)



class AnyAdapts(object):
    implements(IB)
    adapts(None, INoB)
    def __init__(self, a, b):
        self.contexts = [a, b]
    def show(self, name = 'shane'):
        for context in self.contexts:
            try: context.say(name)
            except AttributeError:
                print 'Context %s has no say!' % context


register_adapter(AnyAdapts)
a = A()
noib = NoIB()
adapted = query_multi_adapter((a, noib), IB)
