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
import sys

from avr_lib import *
from test import Test

from ion import Factory

class CountersAndRelaysTester(Test):
    def __init__(self, **kw):
        self.relay1_counts = 50
        self.relay2_counts = 100
        super(CountersAndRelaysTester, self).__init__(**kw)
        self._test_name = 'CountersAndRelaysTester'
        self._avr = get_avr()
        return
        
    def runtest(self):
        self.log('Testing relays and counters.')
        relay1count = self.relay1_counts
        relay2count = self.relay2_counts

        self.reset_counters()
        
        for n in range(0, relay1count):
            a = self._avr.set_relay(1, 1)
            time.sleep(.005)
            a = self._avr.set_relay(1, 0)
            time.sleep(.005)

        for n in range(0, relay2count):
            a = self._avr.set_relay(2, 1)
            time.sleep(.005)
            a = self._avr.set_relay(2, 0)
            time.sleep(.005)

        expected_count = relay1count
        self.check_counter(1, relay1count)
        self.check_counter(2, relay1count)
        self.check_counter(3, relay2count)
        self.check_counter(4, relay2count)

        self.log('Counters/relays, found %d errors and %d warnings.' %
            (self._nerrors, self._nwarnings))
            
        self.reset_counters()
        
        return self.passed()
        
    def reset_counters(self):
        for counter in (1, 2, 3, 4):
            self._avr.reset_counter(counter)
        return
    
    def check_counter(self, counter, expected):
        val = self._avr.get_counter(counter)
        if val != expected:
            self.log('ERROR: Counter %d failed, expected %d, got %d.' %
                (counter, expected, val))
            self._nerrors += 1
        return self.passed()
        
f = Factory()
f.register('CountersAndRelaysTester', (CountersAndRelaysTester,))


