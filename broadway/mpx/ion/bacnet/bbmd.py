"""
Copyright (C) 2002 2004 2005 2006 2010 2011 Cisco Systems

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
from mpx.lib.node import CompositeNode
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.bacnet.bvlc import start_bbmd_service, get_bdt_for, \
     The_BBMD_Server, bbmd_status, enable_bbmd, disable_bbmd, \
     update_bbmds, validate_bbmds
from mpx.lib.persistent import PersistentDataObject
from mpx.lib import msglog

class _PersistentBBMDTable(PersistentDataObject):
    def __init__(self, node):
        self.bbmd_table = None
        self.allow_external_edit = None
        self.enable_bbmd = None
        PersistentDataObject.__init__(self, node)
    def save(self):
        PersistentDataObject.save(self)
        msglog.log('interfaces....BBMD', msglog.types.INFO, 'Saved BBMD table to Persistent Storage')

class BACnetBBMD(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self._persistent_table = None
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'enabled', 1, config, int)
        set_attribute(self, 'bbmd_table', [], config)
        set_attribute(self, 'allow_external_table_editor', 1, config, int)
        self.debug = 0
        if self.debug:
            print 'configure bbmd'
            print str(config)
        
    def configuration(self):
        config = CompositeNode.configuration(self)
        dicts = []
        try:
            table = get_bdt_for(self.parent.interface.network)
            for b in table:
                dicts.append( {'ip':b[0], 'port':b[1], 'mask':b[2] } )
        except:
            #must not be started yet
            pass
        self.bbmd_table = dicts
        get_attribute(self, 'bbmd_table', config)
        get_attribute(self, 'allow_external_table_editor', config, str)
        return config
    
    def start(self):
        enable = 0
        if self.debug:
            print 'start bbmd'
            print self.bbmd_table
            print self.enabled
        if self.enabled:
            if self.debug:
                print 'bbmd is enabled'
            p_table = _PersistentBBMDTable(self)
            self._persistent_table = p_table
            p_table.load()
            if p_table.bbmd_table:
                table = p_table.bbmd_table
                enable = p_table.enable_bbmd
            else: #no persistent data, read config
                table = []
                for b in self.bbmd_table:
                    table.append((b['ip'], b['udp_port'], b['mask'],))
                    if self.debug:
                        print str(b)
                if len(table):
                    enable = 1
            if self.debug:
                print str(table)
                print 'start bbmd_service'
            start_bbmd_service (self.parent.interface, table, self)
            if enable:
                enable_bbmd(self.parent.interface.network)
        CompositeNode.start(self)
    def stop(self):
        try:
            disable_bbmd(self.parent.interface.network)
            self._persistent_table = None
        except:
            msglog.exception()
        CompositeNode.stop(self)
    def save_table(self, table): #called from BDT update
        if self._persistent_table is None:
            self._persistent_table = _PersistentBBMDTable(self)
        p_table = self._persistent_table
        p_table.bbmd_table = table
        p_table.allow_external_edit = self.allow_external_table_editor
        p_table.save()
    def destroy_table(self): #remove the persistent table from disk
        if self._persistent_table is None:
            self._persistent_table = _PersistentBBMDTable(self)
        self._persistent_table.destroy()
        self._persistent_table = None
    def save_enable_bbmd_flag(self, flag):
        if self._persistent_table is None:
            self._persistent_table = _PersistentBBMDTable(self)
        p_table = self._persistent_table
        p_table.enable_bbmd = flag
        p_table.save()
        
            
        
        
def factory():
    return BACnetBBMD()