"""
Copyright (C) 2003 2004 2005 2010 2011 Cisco Systems

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
import string, types
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.node import CompositeNode
from mpx.lib import msglog
from mpx.lib.exceptions import EAlreadyRunning, EInvalidValue, ENotRunning
from mpx.lib.event import EventProducerMixin

##
# MemoryNode: Monitors system RAM statuses (essentially data
# returned by Linux/bash "free" command.
#
class MemoryNode(CompositeNode,EventProducerMixin):
    def __init__(self):
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
        self._running = 0
        return
    def configure(self, cd):     
        CompositeNode.configure(self, cd)
        set_attribute(self, 'debug', 0, cd, int)
        return
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'debug', cd)
        return cd
    def start(self):
        if self._running != 0:
            raise EAlreadyRunning('MemoryNode')
        meminfo_dict = self._get_data_dict()
        # Create child _PropAttr nodes:
        for record_name in meminfo_dict.keys():
            record = _Record()
            cd = {'parent':self,'name':record_name}
            record.configure(cd)
        CompositeNode.start(self) # starts newly-created kids, too
        self._running = 1
        return
    def stop(self):
        if self._running == 0:
            raise ENotRunning('MemoryNode')
        self._running = 0
        CompositeNode.stop(self)
        for record in self.children_nodes():
            record.prune()
        return
    def get(self, skipCache=0):
        meminfo_dict = self._get_data_dict()
        free = float(meminfo_dict['MemFree'])
        buffers = float(meminfo_dict['Buffers'])
        cached = float(meminfo_dict['Cached'])
        total = float(meminfo_dict['MemTotal'])
        total_free = free + buffers + cached
        percentage_free = total_free / total * 100.0
        return percentage_free
    def _get_data_dict(self):
        file_path = '/proc/meminfo'
        fd = open(file_path, 'r')
        lines = []
        lines = fd.readlines()
        fd.close()
        data_dict = {}
        if string.split(lines[0])[0] == 'total:':
            #Skip summaroy lines if they exist (dropped in Linux 2.6)
            for i in range(3):
                lines.pop(0)            
        for line in lines:
            line_elems = string.split(line)
            key = line_elems[0][:-1]
            value_list = line_elems[1:]
            factor = 1.0 / 1024.0
            try: # test for unit label in value_list; remove if found
                i = int(value_list[-1])
            except ValueError:
                label = value_list.pop(-1)
                if label == 'kB':
                    factor = 1.0
            value_list_int = []
            for value in value_list:
                value_list_int.append(int(float(value) * factor))
            data_dict[key] = value_list_int[0]
        return data_dict

    ##
    # tickle: Called periodically by parent "resource" node to
    # update data.
    #
    def tickle( self ):
        return

class _Record(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        return
    def get(self, skipCache=0):
        value = self.parent._get_data_dict()[self.name]
        return value
    
def factory():
    return MemoryNode()
