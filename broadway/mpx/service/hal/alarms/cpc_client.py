"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
from mpx.lib.scheduler import scheduler
from mpx.lib.node import as_node_url
from mpx.cpc.lib.utils import CpcAlarm
from mpx.lib import msglog
from mpx.lib.threading import Thread

debug = 0

class CpcClient(Client):
   def __init__(self, cpc_uhp_node):
      Client.__init__(self)
      self._cpc_uhp_node = cpc_uhp_node
      self._thread = None
      self._go = 1
      return
   def configure(self, config):
      set_attribute(self, 'period', 60.0, config, float)
      Client.configure(self, config)
   def configuration(self):
      config = Client.configuration(self)
      get_attribute(self, 'period', config, float)
      return config
   def start(self):
      Client.start(self)
      self._thread = Thread(None, self._poll_alarms)
      self._go = 1
      self._thread.start()
      return
   def stop(self):
      self._go = 0
      timeout = 30.0
      self._thread.join(timeout)
      if self._thread.isAlive():
         msglog.log('mpx',msglog.types.ERR,'%s failed to terminate its ' \
                    '_poll_alarms thread within %s sec.' % (as_node_url(self),timeout))
      Client.stop(self)
      return
   def _poll_alarms(self): # thread
      while 1:
         ideal_alarms = []
         cpc_alarms = self._cpc_uhp_node.get_alarms()
         for cpc_alarm in cpc_alarms:
            if not isinstance(cpc_alarm, CpcAlarm): # could be None or Exception
               continue
            src = '%s:%s:%s,%s:%s' % (cpc_alarm.device_name, str(cpc_alarm.item), \
                                      cpc_alarm.item_num, str(cpc_alarm.obj), \
                                      cpc_alarm.obj_num)
            tm_tuple = (cpc_alarm.orig_date[0], cpc_alarm.orig_date[1], cpc_alarm.orig_date[2], \
                  cpc_alarm.orig_time[0], cpc_alarm.orig_time[1], 0, 0, 0, -1)
            tm_sec = time.mktime(tm_tuple)
            state = 'Not acked'
            if cpc_alarm.ack_date >= cpc_alarm.orig_date:
               state = 'Acked'
            type = 'Alarm'
            if cpc_alarm.type == 0:
               type = 'Notice'
            i = cpc_alarm.text.find('\x00')
            data = cpc_alarm.text[:i]
            ideal_alarm = Alarm(id=cpc_alarm.id,
                                type=type,
                                source=src,
                                timestamp=tm_sec,
                                data=data,
                                state=state)
            ideal_alarms.append(ideal_alarm)
            msglog.log('mpx',msglog.types.INFO,'CPC Alarm: %s' % ideal_alarm.as_list()) # legal protection in case CPC eqpt fails or Costco doesn't see alarm
         if len(ideal_alarms) > 0:
            ae = NewAlarmsEvent(self, ideal_alarms)
            self.parent.event_generate(ae)
         for i in range(30):
            if self._go == 0:
               return
            time.sleep(1.0)
      return
      
      
      
      
        