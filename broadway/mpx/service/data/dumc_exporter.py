"""
Copyright (C) 2004 2010 2011 Cisco Systems

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
from mpx.lib.configure import REQUIRED,set_attribute,get_attribute
from mpx.lib.exceptions import ENoData
from mpx.lib.threading import Thread
from _exporter import Exporter
from _formatter_exceptions import EInconsistantFormat,EIncompatiableFormat
from _transporter_exceptions import ETransporter
from threading import Lock
from mpx.lib.configure import as_boolean
from mpx.lib import msglog

class DumcExporter(Exporter):
    def __init__(self):
        Exporter.__init__(self)
        self.running = 0
        self._lock = Lock()
    def msglog(self,msg,force=0):     
        if self.debug or force:
            msglog.log('broadway.mpx.service.data.periodic_exporter',
                       msglog.types.DB,msg) 
    def configure(self,config):
        set_attribute(self,'debug',0,config,as_boolean)
        set_attribute(self,'column','entry',config)
        set_attribute(self,'multi_threaded',1,config,as_boolean)
        Exporter.configure(self,config)
    def configuration(self):
        config = Exporter.configuration(self)
        get_attribute(self,'debug',config,str)
        get_attribute(self,'column',config,str)
        get_attribute(self,'multi_threaded',config,str)
        return config
    def start(self):
        self.running = 1
        Exporter.start(self)
        return
    def stop(self):
        self.running = 0
        Exporter.stop(self)
    def export(self,value):
        if self.multi_threaded:
            thread = Thread(name=self.name,target=self._export,args=(value,))
            thread.start()
        else:
            self._export(value)
    def _export(self,value):
        data = self.log.get_range(self.column,value,value)
        if not data:
            raise ENoData(self.column,value,value)
        self.msglog('Sending data to formatter.')
        output = self.formatter.format(data)
        self.msglog('Sending formatted data to transporter.')
        self.transporter.transport(output)
        self.msglog(('Rows with %s = %s exported.' % (self.column,value)))
        return
    def scheduled_time(self):
        return time.time()
def factory():
    return DumcExporter()
