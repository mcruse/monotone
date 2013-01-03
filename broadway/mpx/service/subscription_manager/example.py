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
##
# [mevans@fearfactory native]$ . ./tools/penvironment.rc
# [mevans@fearfactory native]$ ./penvironment.d/etc/rc.mfw -i
# NEED TO SET COM PORT MAPPINGS (in mpx/ion/host/pc.py)
# cat: /home/mevans/bld/trunk/native/penvironment.d/etc/mpxinit.conf: ...
# cat: /home/mevans/bld/trunk/native/penvironment.d/etc/mpxinit.conf: ...
# WARNING: init process not signalled.
# XMLHandler started
# >>> from mpx.service.subscription_manager.example import *

# Things we'll need.
from mpx.lib.node import as_internal_node
from mpx.lib.node import as_node_url
import time

# The Subscription Manager is an implicit child of /services which can be
# referenced via the Node Tree, or directly via the singleton reference:
from mpx.service.subscription_manager import SUBSCRIPTION_MANAGER

# I'd rather type less.
sm = SUBSCRIPTION_MANAGER

# Create a new polled subscription (one that the consumer must check for
# updates to the values).  This mode is primarily intended for client software
# that wants to provide 'real-time' updates without blocking.
polled_sid = sm.create_polled({'hour':'/services/time/local/hour',
                               'status':'/services/status',
                               'minute':'/services/time/local/minute',
                               'second':'/services/time/local/second',
                               'milliseconds':
                               '/services/time/local/milliseconds'})

# Get the values that have changed.
polled_values = sm.poll_changed(polled_sid)

print """\
# The returned object is a dictionary whose keys are the Node IDs supplied
# when the subscription was created/modified."""
polled_keys = polled_values.keys()
print polled_keys # => ['status', 'second', 'milliseconds', 'minute', 'hour']

print """\
# If no values are 'ready' the first time you invoked poll_changed(), or if no
# values have changed since the last time you invoked poll_changed(), then
# an empty dictionary is returned.

# The values indexed by the Node IDs are known as the 'result dictionary',
# which contain four keys: 'cached', 'timestamp', 'changes', and 'value':
"""

def print_result_dictionary(rd):
    print """Result Dictionary:
    value:     %r
    timestamp: %r
    cached:    %r
    changes:   %r""" % (rd['value'], rd['timestamp'],
                        rd['cached'], rd['changes'])
    return

def print_results(results):
    for node_id, result_dictionary in results.items():
        print "Node ID: %r" % node_id
        print_result_dictionary(result_dictionary)
        print ""

print "*** Initial Results ***"
print_results(polled_values)

for i in range(0,3):
    time.sleep(0.5)
    print "\n*** Polled Results after 1/2 second (pass %d) ***" % (i+1)
    polled_values = sm.poll_changed(polled_sid)
    print_results(polled_values)

sm.add(polled_sid, 'time','/services/time')

sm.add(polled_sid, 'no get()','/services') # Bug, exception miscompares.

sm.remove(polled_sid, 'no get()')          # Bug, not removed from active list.

sm.add(polled_sid, 'bogus','/services/bogus')

