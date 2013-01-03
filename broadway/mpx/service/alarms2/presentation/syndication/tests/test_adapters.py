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
from mpx.componentry.tests import verify_class
from mpx.www.w3c.syndication.rss1.interfaces import IRSS1Content
from mpx.www.w3c.syndication.rss2.interfaces import IRSS2Content
from mpx.www.w3c.syndication.atom.interfaces import IAtomContent
from mpx.service.alarms2.presentation.syndication.atom.adapters import AtomSyndicator
from mpx.service.alarms2.presentation.syndication.rss2.adapters import RSS2Syndicator

assert verify_class(IRSS2Content, RSS2Syndicator), (
    'fails interface verify')

assert verify_class(IAtomContent, AtomSyndicator), (
    'fails interface verify')

from mpx.service.alarms2.tests.test_alarm import alarm_manager






rss2 = IRSS2Content(alarm_manager)
rssout = open('/var/www/sgreen/dev/output/rss2test.rss', 'w')
rssout.write(rss2.render())
rssout.close()

atom = IAtomContent(alarm_manager)
atomout = open('/var/www/sgreen/dev/output/atom.xml', 'w')
atomout.write(atom.render())
atomout.close()

print rss2.render()

print atom.render()

import time
from mpx.lib.node import as_node
am = as_node('/services/Alarm Manager')
def timed_op(alarm, name, count):
    numevents = len(alarm.get_events())
    tstart = time.time()
    for i in range(count):
        getattr(alarm, name)(timed_op, tstart, {})
    tend = time.time()
    tlapse = tend - tstart
    print 'Calling %s on alarm with %s events %s times took: %s' % (name, numevents, count, tlapse)
    print '\tEach call took ~%s sec.' % (tlapse / count)
    return tlapse
