"""
Copyright (C) 2007 2010 2011 Cisco Systems

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

from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute
from mpx.lib.configure import REQUIRED

from mpx.service.logger.column import Column
from mpx.service.logger.column import Columns
from mpx.service.logger.log import Log

class TrapLog(Log):
    __node_id__ = '67066bfc-a5cb-4114-bb79-ccb173d4fd66'
    def log_trap(self,
                 version, context_engine_id, context_name, address,
                 sysUpTime, trap,
                 trap_enterprise,
                 varBinds,
                 logtime):
        self.add_entry([version,
                        context_engine_id,
                        context_name,
                        address,
                        sysUpTime,
                        trap,
                        trap_enterprise,
                        varBinds,
                        logtime,])
        return

class TrapColumns(Columns):
    __node_id__ = '21a9b271-a8c2-4fb8-916e-c5a80327141a'

class TrapExporters(CompositeNode):
    __node_id__ = 'f29796a9-63aa-4163-965a-4136074d45d4'

class TrapColumn(Column):
    __node_id__ = '231328de-d2a2-4f41-916e-8bce915f6bc3' # Stub
    klass_position = REQUIRED
    klass_sort_order = 'none'
    klass_type = 'column'
    #
    def configure(self,config):
        set_attribute(self, 'position', self.klass_position, config, int)
        set_attribute(self, 'sort_order', self.klass_sort_order, config)
        set_attribute(self, 'type', self.klass_type, config)
        Column.configure(self,config)
        return

class TrapVersionColumn(TrapColumn):
    __node_id__ = 'a75afc49-4825-4d20-92fe-db67ad07e827'
    klass_position = 0

class TrapContextEngineIdColumn(TrapColumn):
    __node_id__ = '221da4e0-023f-41c6-a152-9fcb5f352b65'
    klass_position = 1

class TrapContextNameColumn(TrapColumn):
    __node_id__ = '5eac418e-a754-44e0-9414-4244cc0e111b'
    klass_position = 2

class TrapAddressColumn(TrapColumn):
    __node_id__ = 'b156352c-6e49-4be0-b7f7-d1d0eee2cfb7'
    klass_position = 3

class TrapSysUpTimeColumn(TrapColumn):
    __node_id__ = '7a4b6c90-3969-415f-8830-937e691b93fc'
    klass_position = 4

class TrapTrapColumn(TrapColumn):
    __node_id__ = '774b84c2-f922-4381-a651-bd85c692bb34'
    klass_position = 5

class TrapTrapEnterpriseColumn(TrapColumn):
    __node_id__ = '86a0e986-10f5-4f2f-8162-db9aa78da331'
    klass_position = 6

class TrapVarBindsColumn(TrapColumn):
    __node_id__ = 'cd60d3ca-8ca5-4194-bea2-9812cf0d57c5'
    klass_position = 7

class TrapLogTimeColumn(TrapColumn):
    __node_id__ = 'dfd0f9f1-c777-4ee7-a5c8-f17f7dcbb843'
    klass_position = 8

