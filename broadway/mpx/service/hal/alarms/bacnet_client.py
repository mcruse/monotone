"""
Copyright (C) 2003 2005 2010 2011 Cisco Systems

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

from mpx.service.hal.alarms import Alarm, NewAlarmsEvent
from mpx.service.hal.client import Client
from mpx.lib.configure import set_attribute, get_attribute, as_boolean
from mpx.lib.node import as_node
from mpx.lib.scheduler import scheduler
from mpx.lib.bacnet.trane import eventlog

debug = 0

# @fixme: Shortly this code will be refactored to use its own thread
#         instead of doing potentially long tasks via the scheduler.
class BACnetClient(Client):
   def __init__(self):
      Client.__init__(self)
      self.debug = 0
      self.node = None
      self.h_node = None
      self.sid = None
      self.old_alarms = []
   def configure(self,config):
      if debug:
         print 'In BACnetClient.configure with %s.' % str(config)
      set_attribute(self,'node','/interfaces/eth0/BACnetIP/BCU-01 (1)',config)
      Client.configure(self,config)
   def configuration(self):
      config = Client.configuration(self)
      get_attribute(self,'node',config)
      return config
   def start(self):
      Client.start(self)
      self.h_node = as_node(self.node)
      self.sid = scheduler.after(15, self.poll_alarms)
   def stop(self):
      Client.stop( self )
      if self.sid:
         scheduler.cancel(self.sid)
   # get_alarms: Returns all the alarms/events currently stored in
   #             the BCU.
   def get_alarms(self):
      alarms = []
      t = eventlog.Trane_EventLog()            
      alarms += t.read(self.h_node.device_info.network,
                       self.h_node.instance)
      return alarms
   def poll_alarms(self):
      if not self._running:
         return

      if debug > 1:
         print '%f: In poll_alarms().' % time.time()

      alarms = self.get_alarms()
  
      ret_alarms = []
      
      for x in alarms:
         if not x in self.old_alarms:
            if debug:
               print 'Found a new alarm: %s' % str(x)

            # Note: @fixme:  At some point we will probably do some filtering
            #       on the "alarms" we get back from the BCU because apparently
            #       they may include some event type information for which we
            #       don't want to create an Alarm Event.  FredD apparently
            #       has the information for differentiating between events
            #       and real alarms from a BCU.

            # Note: x looks like:
            # {'priority': '', 'ack': 'No', 'from': 'BCU-01', 'SN': 0,
            #  'date': 1068221677.0, 'type': 'Watchdog Timeout',
            #  'detail': ''
            # }
            a = Alarm(id=x['SN'],
                      type=x['type'],
                      source=x['from'],
                      timestamp=x['date'],
                      data=x['detail'],
                      priority=x['priority'],
                      acked=x['ack'])
            if debug:
               print 'Got new alarm: %s.' % str(a)
            ret_alarms.append(a)
         else:
            if debug:
               print 'Ignoring alarm, it has already been raised reported'
      if ret_alarms:
         self.parent.put_alarms(ret_alarms)
      # Note: @fixme: old_alarms should be a PDO so that we don't resend alarms
      #       that have already been seen every time we start up.  For now this
      #       behavior may actually be useful for testing but probably will
      #       not be a "feature" in the real world.
      self.old_alarms = alarms
      self.sid = scheduler.after(15, self.poll_alarms)
