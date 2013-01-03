"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
from mpx_test import DefaultTestFixture, main

import sys

from mpx.lib import pause
from mpx.lib.node.simple_value import SimpleValue

from __init__ import PeriodicRelayDriver

class TestCase(DefaultTestFixture):
    VERBOSE = 0
    def PRINT(self, fmt, *args, **kw):
        quite = 0
        if kw.has_key('quite'):
            quite = kw['quite']
        if self.VERBOSE and not quite:
            sys.stderr.write("VERBOSE:  %s" % (fmt % args))
            sys.stderr.flush()
    def _fault_on_output_not(self, pts, value, quite):
        o = pts.output.get()
        if o != value:
            msg = 'Auto failed to drive output(%r) == %r.' % (o, value)
            self.PRINT(msg + '\n')
            raise msg
        return
    def _exercise_override(self, pts):
        for v in (0, 1, 0, 1, 1, 1, 0, 1, 0):
            pts.set(v)
            v = pts.get()
            self.PRINT("OVERRIDE TO %s\n", v)
            self._fault_on_output_not(pts, v, 0)
    def _exercise_auto(self, pts):
        for v in (0, 1, 0, 1, 1, 1, 0, 1, 0):
            self.PRINT("pts.input.set(%r)\n", v)
            pts.input.set(v)
            for i in range(0,10):	# Maximum time to wait is pts.period*2
                o = pts.output.get()
                if o != v:
                    pause(pts.period/5)
                    continue
                break
            self._fault_on_difference(pts, 0)
        return
    def _fault_on_difference(self, pts, quite):
        i = pts.input.get()
        o = pts.output.get()
        if o != i:
            msg = 'Auto failed to drive output(%r) == input(%r).' % (o, i)
            self.PRINT(msg + '\n')
            raise msg
        return
    def test_10_PeriodicRelayDriver(self, quite=0):
        self.PRINT("ENTER: test_10_PeriodicRelayDriver: %s\n", "*"*15,
                   quite=quite)
        result = PeriodicRelayDriver()
        self.PRINT("EXIT:  test_10_PeriodicRelayDriver: %s\n", "*"*15,
                   quite=quite)
        return result
    def test_20_PeriodicRelayDriver_config(self, quite=0):
        self.PRINT("ENTER: test_20_PeriodicRelayDriver_config: %s\n",
                   "*"*15, quite=quite)
        pts = self.test_10_PeriodicRelayDriver(1)
        output = SimpleValue()
        output.configure({'name':'output',
                          'parent':None,
                          'value':0})
        input = SimpleValue()
        input.configure({'name':'input',
                          'parent':None,
                          'value':0})
        level = 0 # No debugging output.
        if TestCase.VERBOSE != 0:
            level = 2 # DEBUG2
        pts.configure({'parent':output,
                       'name':'periodic_relay_driver',
                       'input':input,
                       'debug':level})
        self.PRINT("EXIT:  test_20_PeriodicRelayDriver_config: %s\n",
                   "*"*15, quite=quite)
        return pts
    def test_30_PeriodicRelayDriver_auto(self, quite=0):
        self.PRINT("ENTER: test_30_PeriodicRelayDriver_set: %s\n",
                   "*"*15, quite=quite)
        pts = self.test_20_PeriodicRelayDriver_config(1)
        pts.input.set(0)
        pts.output.set(0)
        pts.start()
        self.PRINT("AUTO MODE:\n", quite=quite)
        pts.set(2)
        # It's in AUTO...
        self.PRINT("pts.input.set(1)\n", quite=quite)
        pts.input.set(1)
        pause(pts.period*2)
        self._fault_on_difference(pts, quite)
        self._exercise_auto(pts)
        self.PRINT("EXIT:  test_30_PeriodicRelayDriver_set: %s\n",
                   "*"*15, quite=quite)
        pts.stop()
        return
    def test_40_PeriodicRelayDriver_auto_to_on_and_back(self, quite=0):
        self.PRINT("ENTER: test_40_PeriodicRelayDriver_auto_to_on_and_back:" +
                   " %s\n",
                   "*"*5, quite=quite)
        pts = self.test_20_PeriodicRelayDriver_config(1)
        pts.input.set(0)
        pts.output.set(0)
        pts.start()
        # It's in AUTO...
        self.PRINT("AUTO MODE:\n", quite=quite)
        pts.set(2)
        self._exercise_auto(pts)
        # Drive the reley using overrides.
        self._exercise_override(pts)
        # Now switch back to AUTO...
        self.PRINT("AUTO MODE:\n", quite=quite)
        pts.set(2)
        self._exercise_auto(pts)
        pts.stop()
        self.PRINT("EXIT:  test_40_PeriodicRelayDriver_auto_to_on_and_back:" +
                   " %s\n", "*"*5, quite=quite)
        return
    def test_50_depricated_location(self, quite=0):
        self.PRINT("ENTER: test_50_depricated_location:" +
                   " %s\n",
                   "*"*5, quite=quite)
        from relay_driver import PeriodicRelayDriver
        self.PRINT("EXIT:  test_50_depricated_location:" +
                   " %s\n", "*"*5, quite=quite)
        return
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    TestCase.VERBOSE = 1
    main()
