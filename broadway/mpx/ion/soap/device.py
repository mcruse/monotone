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
## @notes Class TCS
##        Simple abstraction for dynamically
##        discovering TCS nodes and presenting
##        them as nodes in the framework

import array
import time
import random

from mpx.lib import msglog
from mpx.lib.node import CompositeNode, ConfigurableNode
from mpx.lib.configure import set_attribute, get_attribute, \
     as_boolean, as_onoff, REQUIRED
from mpx.lib.exceptions import EAlreadyRunning, \
     ETimeout, EInvalidValue, MpxException, ENoSuchName
from mpx.lib.soap.suds import build_and_send_request as bs
from mpx.lib.soap.suds import _HTTPConnection
from mpx.lib.threading import Lock

debug = 0

class Result:
    ##
    # The node's value.
    #
    value = None
    ##
    # The timestamp of when the value was actually retrieved
    # from the device.  This is important in some cases where
    # caching is used as the timestamp will show when the value
    # was last updated.
    timestamp = None
    ##
    # True iff the value returned was a cached value.
    cached = 1
class Host(CompositeNode):
    
    version = '0.0'
    def __init__(self):
        self.conn = None
        CompositeNode.__init__(self)
    
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self,'debug', debug, config, as_boolean)
        set_attribute(self,'host',REQUIRED,config, str)
    
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'debug', config, as_onoff)
        get_attribute(self, 'host',config)
        self.__node_id__ = '120071'
        get_attribute(self, '__node_id__', config, str)
        return config

   
    ## get format list of nodes and their values
    #  @returns format list of values
    #
    def get(self, skipCache=0):
        info =        'Version: %s\n' % Host.version         
        return info
        
class Action(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self._last_exception = None
        self.average_access_time = None
        self._action_lock = Lock()
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self,'debug', debug, config, as_boolean)
        set_attribute(self,'post',REQUIRED,config, str)
        set_attribute(self,'server',REQUIRED, config, str)
        set_attribute(self,'action',REQUIRED, config, str)
        set_attribute(self,'ttl',1.0, config, float)
    
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'debug', config, as_onoff)
        get_attribute(self, 'post',config, str)
        get_attribute(self, 'server', config, str)
        get_attribute(self, 'action', config, str)
        get_attribute(self, 'ttl', config, str)
        self.__node_id__ = '120072'
        get_attribute(self, '__node_id__', config, str)
        return config

    def get(self, skipCache=0):
        if self._last_exception:
            raise self._last_exception
        info = 'Number of Children: %s, Average access time: %s' % (len(self.children_nodes()), self.average_access_time)
        return info
    def get_children_values(self): #get all readable children
        list = []
        for child in self.children_nodes():
            if hasattr(child,'Name'):
                if hasattr(child,'Type'):
                    list.append([['Name',child.Name], ['Type',child.Type]])

        host = self.parent.host
        post = self.post
        action_server = self.server
        action = self.action

        try:
            conn = self.parent.conn
            if conn:
                if conn.sock is None: #since it was closed
                    self.parent.conn = _HTTPConnection(host)
            else:
                self.parent.conn = _HTTPConnection(host)
            conn = self.parent.conn
        except Exception, e:
            self._last_exception = e
            raise e

        values = {}
        trys = 3
        while trys > 0:
            try:
                start_time = time.time()
                values = bs(host, post, action_server, action, list, conn)
                end_time = time.time()
                time_to_run = end_time - start_time
                if time_to_run > 10.0:
                    print 'Excessive time to access SOAP server: ', time_to_run
                if self.average_access_time is None: self.average_access_time = time_to_run
                self.average_access_time = ((self.average_access_time * 9.0) + time_to_run) / 10.0
                break
            except ETimeout, e:
                if debug: print 'retry soap server'
                trys = trys - 1
                if trys == 0:
                    self._last_exception = e
                    raise e
            except Exception, e:
                if debug: print 'unknown soap error'
                self._last_exception = e
                raise e
            pass
        for child in self.children_nodes():
            if hasattr(child,'Name'):
                child.result = Result()
                child.result.timestamp = time.time()
                if values.has_key(child.Name):
                    child.soap_attributes = values[child.Name]
                    if child.soap_attributes.has_key('Value'):
                        child.result.value = str(values[child.Name]['Value'])
                    else:
                        child.result.value = None
                else: #missing key
                    child.result.value = ENoSuchName(child.Name, values)
        self._last_exception = None
         
class Point(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.soap_attributes = {}
        self.result = None
    def configure(self, config):
        CompositeNode.configure(self,config)
        set_attribute(self,'debug', debug, config, as_boolean)
        set_attribute(self,'Name',REQUIRED,config, str)
        set_attribute(self,'Type',REQUIRED, config, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self,'debug', config, as_onoff)
        get_attribute(self,'Name',config, str)
        get_attribute(self,'Type', config, str)
        self.__node_id__ = '120073'
        get_attribute(self, '__node_id__', config, str)
        config.update(self.soap_attributes)
        return config
    #raise an exception if no name was found in response
    def _check_result_for_error(self):
        if self.result.value:
            if self.result.value.__class__ == ENoSuchName:
                raise self.result.value
    def _get_result(self): #just get it
        self.parent.get_children_values() #this will update self.result
        self._check_result_for_error()
        return self.result
    def get_result(self, skipCache=0, **keywords): 
        if self.debug: print 'get from cache'
        self.parent._action_lock.acquire()
        try:
            if skipCache:
                if self.debug: print 'skipping cache, get just this point'
                return self._get_result()
            if self.result: #there was a previously cached value, see if it is any good
                now = time.time()
                if (now - self.parent.ttl) < self.result.timestamp:
                    self._check_result_for_error()
                    return self.result #give them the cached result
            return self._get_result()
        finally:
            self.parent._action_lock.release()
    def get(self, skip_cache=0):
        answer = self.get_result(skip_cache)
        if answer is None:
            raise EInvalidValue('Value is missing', str(self.soap_attributes))
        return answer.value
    
