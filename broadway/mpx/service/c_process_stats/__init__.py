"""
Copyright (C) 2006 2007 2010 2011 Cisco Systems

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
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib import msglog
from time import time, ctime

from moab.linux.lib.event_router.c_process_stats import get_c_stat, \
     get_c_stat_names, get_c_stat_log_on_change, get_c_stat_time_last_changed


# CStatNodes are dynamic nodes. Meaning they do not exist in the broadway.xml,
# they do not have nodedefs and they are added during a running framework.

# To find out which CStatNodes are available, you must call children_nodes
# on the CProcessStatsNode.

# CStatNodes will not be added to the framework until at least one thread
# calls children_nodes on the CProcessStatsNode. It was observed that
# the framework will call children_nodes in the start phase. If c stats
# are registered before the start phase their nodes will exist after the
# start phase.

# It is this way because c process stats can be added at any time.

class CStatNode( CompositeNode):

    def __init__(self, c_stat_name):
        CompositeNode.__init__(self)
        self.c_stat_name = c_stat_name

    def get(self):
        cstat = None
        try:
            cstat = get_c_stat(self.c_stat_name)
        except:
            # If this happens, it is probably because the stat disappeared
            self.log_stat_disappeared()
        return cstat

    def configure(self, cd):
        CompositeNode.configure(self, cd)
        try:
            log_on_change = get_c_stat_log_on_change(self.c_stat_name)
        except:
            # If this happens, it is probably because the stat disappeared
            self.log_stat_disappeared()
            return None
        set_attribute(self, 'log_on_change',
                      log_on_change, cd, int)
        set_attribute(self, 'time_last_changed', ctime(0), cd, str)

    def configuration(self):
        cd = CompositeNode.configuration(self)
        try:
            self.log_on_change = get_c_stat_log_on_change(self.c_stat_name)
        except:
            # If this happens, it is probably because the stat disappeared
            self.log_stat_disappeared()
            return None

        if self.log_on_change:
            try:
                last_changed = get_c_stat_time_last_changed(self.c_stat_name)
            except:
                # If this happens, it is probably because the stat disappeared
                self.log_stat_disappeared()
                return None
                
            self.time_last_changed = ctime(last_changed)
        else:
            self.time_last_changed = 'N/A'
            
        get_attribute(self, 'log_on_change', cd, int)
        get_attribute(self, 'time_last_changed', cd, str)
        return cd

    def log_stat_disappeared(self):
        msglog.log('C Stats', msglog.types.INFO,
                   'get_c_stat() error, stat may no longer exist: ' +
                   self.c_stat_name)
        return
        
class CProcessStatsNode( CompositeNode):

    def __init__(self):
        CompositeNode.__init__(self)

    def configure(self, cd):
        CompositeNode.configure(self, cd)

    def children_nodes(self):
        children = CompositeNode.children_nodes(self)

        stats = get_c_stat_names()

        # remove all nodes that do not have a stat
        nodeNameList = []
        for c in children:
            if c.name not in stats:
                c.prune()
            else:
                nodeNameList.append( c.name)
        
        # add all stats to node tree (unless already there)
        for stat in stats:
            if stat not in nodeNameList:
                n = CStatNode(stat)
                cd = { 'name'   : stat,
                       'parent' : self,
                       'log_on_change': -1,
                       'time_last_changed': ''}
                
                n.configure( cd)

        return CompositeNode.children_nodes(self)
