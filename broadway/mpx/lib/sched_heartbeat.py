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
# mpx.service.sched_heartbeat: 
#
import time
from mpx.lib.exceptions import EInternalError
from mpx.lib import msglog
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.scheduler import scheduler

class SchedHeartbeat(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self._running = 0
        self._sid = None
        return
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self,'heartbeat_period',60,cd,int)
        set_attribute(self,'__node_id__','fd953ea3-07d6-4132-8ce1-f85074fac613',cd, str)
        return
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self,'heartbeat_period',cd,int)
        get_attribute(self,'__node_id__',cd,str)
        return cd
    def start(self):
        self._sid = scheduler.after(self.heartbeat_period,self._heartbeat_action)
        assert not self._sid is None, 'SchedHeartbeat.start(): Failed to get non-None sid from scheduler'
        CompositeNode.start(self)
        self._running = 1
        return
    def stop(self):
        self._running = 0
        CompositeNode.stop(self)
        if not self._sid is None:
            scheduler.cancel(self._sid)
            self._sid = None
        return
    def _heartbeat_action(self):
        self._safe_log('Scheduler Heartbeat')
        try:
            self._sid = scheduler.after(self.heartbeat_period,self._heartbeat_action)
        except Exception, e:
            self._safe_log('Failed to re-schedule Scheduler Heartbeat: %s' % str(e))
        return
    def _safe_log(self, msg):
        try:
            msglog.log('mpx:sched_hb',msglog.types.INFO,msg)
        except Exception, e:
            msg = 'SchedHeartbeat: Failed to log "%s": %s\n\r' % (msg,str(e))
            unique_file_name = '/var/mpx/log/ErrorLog' + str(int(time.time()))
            fd = open(unique_file_name,'a+')
            fd.write(msg)
            fd.flush()
            fd.close()
        return
    
    
    
    
    
    
    
    
    