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
import os

from mpx_test import DefaultTestFixture, main

from mpx.lib import factory
from mpx.lib.node import CompositeNode, as_node_url
from mpx.ion.host.arm import arm, ai, ao, di, relay, canbus, dallasbus, counter

class FakeCoprocessor(object):
    def __init__(self):
        self.calibration = arm.default_calibration
        self._coprocessor = None
    def read_response(self, command, *args):
        params = command.split()
        answer = {'command':params[0], 'error':None, 'values':[0.0]}
        print answer
        return answer

_FakeCoprocessor = FakeCoprocessor()

class TestCase(DefaultTestFixture):
    def test_ai(self):
        ai1 = ai.factory()
        config = {'parent':None, 'name':'ai1', 'id':1, 'mode':'volts', 'coprocessor':_FakeCoprocessor}
        ai1.configure(config)
        return
    def test_ao(self):
        ao1 = ao.factory()
        config = {'parent':None, 'name':'ao1', 'id':1, 'coprocessor':_FakeCoprocessor}
        ao1.configure(config)
        return
    def test_di(self):
        di1 = ai.factory()
        config = {'parent':None, 'name':'di1', 'id':1, 'coprocessor':_FakeCoprocessor}
        di1.configure(config)
        return
    def test_relay(self):
        do1 = ai.factory()
        config = {'parent':None, 'name':'do1', 'id':1, 'coprocessor':_FakeCoprocessor}
        do1.configure(config)
        return
    def test_dallas(self):
        return
    def test_can(self):
        return

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

