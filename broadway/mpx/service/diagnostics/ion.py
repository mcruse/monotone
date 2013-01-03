"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import urllib
import httplib

from urlparse import urlparse

from Queue import Queue

from mpx.lib import msglog

from mpx.lib.node import CompositeNode

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute

from mpx.lib.threading import Thread

from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENotImplemented

class DiagContainer(CompositeNode):
    def configure(self, cd):
        super(DiagContainer, self).configure(cd)
        set_attribute(self, 'tech_support', 0, cd, int)
        return
    
    def configuration(self):
        cd = super(DiagContainer, self).configuration()
        get_attribute(self, 'tech_support', cd)
        return cd
        
    def nodebrowser_handler(self, nb, path, node, node_url): 
        sections = nb.get_default_presentation(node, node_url)
        if not self.tech_support:
            # suppress the child nodes section of the display
            sections['node-children'] = ''
        return nb.get_default_view_for(sections)

class DiagIon(CompositeNode):
    def __init__(self):
        self._worker_queue = Queue()
        return
        
    def configure(self, cd):
        super(DiagIon, self).configure(cd)
        set_attribute(self, 'factory', REQUIRED, cd)
        #@todo - allow config options
        return
    
    def configuration(self):
        cd = super(DiagIon, self).configuration()
        get_attribute(self, 'factory', cd)
        return cd
    
    def start(self):
        self._test = getattr(Factory(), self.factory)()
        for mthd_name in self._test.public:
            try:
                setattr(self, mthd_name, getattr(self._test, mthd_name))
            except:
                msglog.exception()
        self._worker_thread = Thread(target=self._work, args=())
        self._worker_thread.start()
        super(DiagIon, self).start()
        return
        
    def get(self, skipCache=0):
        rslt = None
        if self.parent.tech_support:
            rslt = self._test.runtest()
        return rslt
        
    def get_with_callback(self, callback_url):
        self._submit_work(callback_url)
        return
        
    def set_property(self, prop_name, prop_value):
        if not hasattr(self._test, prop_name):
            raise EInvalidValue(
                    'set_property',
                    prop_value,
                    'Error setting unknown property.'
                )
        setattr(self._test, prop_name, prop_value)
        return
        
    def _submit_work(self, callback):
        self._worker_queue.put(callback)
        return
        
    def _work(self):
        NETLOC = 1
        PATH = 2
        while 1:
            callback = self._worker_queue.get()
            try:
                result = self.get()
            except:
                msglog.exception()
                result = 'None'
            try:
                data = urllib.urlencode({'result':result})
                p_url = urlparse(callback)
                conn = httplib.HTTPConnection(p_url[NETLOC])
                conn.request('POST', p_url[PATH], data)
                rsp = conn.getresponse()
                msg = '%s sent a response of %s to %s.' % \
                    (self.as_node_url(), result, callback)
                msglog.log(
                        'broadway',
                        msglog.types.INFO,
                        msg
                    )
            except:
                msglog.exception()
        return

class Factory(object):
    __instance = None
    def __init__(self):
        if Factory.__instance is None:
            Factory.__instance = Factory.__impl()
            self.__dict__['_Factory__instance'] = Factory.__instance
        return
        
    def __getattr__(self, attr):
        return getattr(self.__instance, attr)
        
    def __setattr__(self, attr, value):
        return setattr(self.__instance, attr, value)
        
    class __impl(object):
        def register(self, method_name, constructor):
            setattr(self, method_name, apply(Functor, constructor))
            return
            
        def unregister(self, method_name):
            delattr(self, method_name)
            return
            
class Functor(object):
    def __init__(self, function):
        self._function = function
        return
        
    def __call__(self):
        return apply(self._function)
