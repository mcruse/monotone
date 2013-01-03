"""
Copyright (C) 2011 Cisco Systems

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
import inspect
from threading import RLock
from mpx.lib import msglog
from mpx.lib.node import is_node
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.rna import _RemoteMethod
from mpx.lib.translator.calculator import Calculator
from mpx.service.subscription_manager.cache import PointCache
from mpx.service.subscription_manager.cache import CachedPoint
from moab.linux.lib import uptime

class CachingCalculator(Calculator):
    """
        Extension of Calculators which leverages Point Caches 
        to leverage Subscription Manager updates for input 
        values.
    """
    def __init__(self):
        self.ttl = 5
        self.inputs = None
        self.last_refresh = 0
        self.synclock = RLock()
        super(CachingCalculator, self).__init__()
    def start(self):
        if not self.inputs:
            self.inputs = PointCache()
            self.inputs.configure({"name": "inputs", "period": 0, 
                                   "polled": True, "parent": self})
        return super(CachingCalculator, self).start()
    def refresh(self):
        self.inputs.refresh()
        self.last_refresh = uptime.secs()
    def since_refresh(self):
        return uptime.secs() - self.last_refresh
    def should_refresh(self):
        return self.since_refresh() > self.ttl
    def setup_context(self):
        running = self.inputs.is_running()
        if running:
            self.inputs.stop()
        for child in self.inputs.children_nodes():
            msglog.warn("Pruning input child: %s." % child)
            child.prune()
        context = super(CachingCalculator, self).setup_context()
        if running:
            self.inputs.start()
        return context
    def as_node_input(self, name, node):
        if not node.has_method("get"):
            # The above if statement fails when nodes don't resolve.
            raise ValueError("node has no 'get' method: %s" % node)
        source = as_node_url(node)
        if self.inputs.has_child(name):
            node = self.inputs.get_child(name)
            if source != node.source:
                raise ValueError("Input with name exists: %r" % name)
            msglog.warn("Input exists: %r, %r" % (name, source))
        else:
            running = self.inputs.is_running()
            if running:
                self.inputs.stop()
            node = CachedPoint()
            node.configure({"name": name, 
                            "source": source, 
                            "parent": self.inputs})
            if running:
                self.inputs.start()
        return super(CachingCalculator, self).as_node_input(name, node)
    def evaluate(self, *args, **kw):
        self.synclock.acquire()
        try:
            if self.should_refresh():
                self.refresh()
            result = super(CachingCalculator, self).evaluate(*args, **kw)
        finally:
            self.synclock.release()
        return result
    def _evaluate(self, value_map):
        try:
            answer = eval(self.compiled_statement, globals(), value_map)
        except:
            msglog.warn("%s evaluate failed with inputs: %r." % (self, value_map))
            raise
        return answer
