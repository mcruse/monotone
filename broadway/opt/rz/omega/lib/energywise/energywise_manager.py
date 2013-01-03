"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
import sys
import os
import mpx.lib
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node_url 
from mpx.lib.node import as_node 
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.configure import REQUIRED
from mpx.lib import msglog
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENameInUse
from mpx.lib.persistent import PersistentDataObject
from energywise_api import EnergywiseSwitch
from energywise_api import EnergywiseDomain
from threading import Lock
from mpx.service.garbage_collector import GC_NEVER

class EnergywiseManager(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self._pdo_lock = Lock()
        self._pdo = None
        self.__running = False
        self.debug = 0
        return

    def configure(self,config):
        if self.debug:
            msglog.log('EnergywiseManager:', msglog.types.INFO,
                       'Inside configure' )
        CompositeNode.configure(self, config)
        set_attribute(self, 'debug', 0, config, int)
        return

    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'debug', config, str)
        return config

  

   # def configure_trend_in_switches(self, start_node, frequency):
    #    for child in start_node.children_nodes():
     #       if child.children_nodes():
      #          self.configure_trend_in_switches(child, frequency)
       #     else:
                # reached upto leaf, each energywise switch has trends as child
        #        child.new_trend(frequency)
        #return

    def delete_trend_configuration(self, trend_domain):
        self._pdo_lock.acquire()
        try:
            if self._pdo.trends.has_key(trend_domain): 
                # stop logging as well
                del self._pdo.trends[trend_domain]
            self._pdo.save()
        finally:
            self._pdo_lock.release()
        return
    def delete_trends(self, trendList):
        if self.debug:
            msglog.log('EnergywiseManager:', msglog.types.INFO, 
                       'Inside delete_trends' )

        for domain in trendList.split(':'):
            if domain:
                domain_node = as_node(domain)
                domain_node.delete_trend()
                self.delete_trend_configuration(domain)
        return
         
    def start(self):
        if self.__running:
            return
        if self.debug:
            msglog.log('EnergywiseManager :', msglog.types.INFO, 'Inside start' )
        CompositeNode.start(self)
#        start_node = as_node('/services/EnergywiseManager/')
#        self.configure_trend_in_switches(start_node, 60)
        self.__running = True
        self._pdo_lock.acquire()
        self._pdo = PersistentDataObject(self, dmtype=GC_NEVER)
        self._pdo.trends = {}
        self._pdo.load()
        self._pdo_lock.release()
        if self.has_child('trends'):
            self.trends = self.get_child('trends')
        else:
            self.trends = CompositeNode()
            self.trends.configure({'parent':self, 'name':'trends'})
            self.trends.start()
        # start trending for saved domains
        for domain,freq in self._pdo.trends.items():
            try:
                start_node = as_node(domain)
               # self.configure_trend_in_switches( start_node,freq )
                start_node.new_trend(freq)
            except:
                self.delete_trend_configuration(domain)
        return

    def get_trends(self):
        return self._pdo.trends.items()

    def add_trend_configuration(self, trend_period, trend_domain):
        self._pdo_lock.acquire()
        self._pdo.trends[trend_domain] = trend_period
        self._pdo.save()
        self._pdo_lock.release()
        return
    def save_trends(self, trend_list):
        # Traverse through _pdo.items and check if new domain is either subset
        # of any configured or superset. 
        # If subset return with msg already covered and dont save this
        # If superset then configure new ones and delete subset from 
        # _pdo.items
        '''Adding and saving trends'''
        for point in reversed(trend_list):
            point_period = point['frequency']
            point_domain = point['domain']
            for  saved_domain,saved_period in tuple(self._pdo.trends.items()):
                if saved_domain == point_domain:
                    if saved_period != point_period:
                        self.delete_trend_configuration(saved_domain)
                        break
            if not self._pdo.trends.has_key(point_domain):
                # add this trend
                try:
                    domain_node = as_node(point_domain)
		    if isinstance(domain_node,EnergywiseSwitch) or isinstance(domain_node,EnergywiseDomain):
                         self.add_trend_configuration(point_period, point_domain)
                         domain_node.new_trend(point_period)
                except Exception:
                    msglog.exception()
                    msglog.log(
                        "Energywise",msglog.types.ERR,
                        "Failed to create trend for %r every %r seconds" 
                        %(point_domain,point_period)
                        )
        return


    def stop(self):
        CompositeNode.stop(self)
        self.__running = False
        return
