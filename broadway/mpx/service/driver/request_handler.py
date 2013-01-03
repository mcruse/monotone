"""
Copyright (C) 2007 2009 2011 Cisco Systems

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
import string
import urllib
import cPickle
from threading import Lock
from HTMLgen import HTMLgen
from mpx.lib import msglog
from mpx.lib.configure import as_boolean
from mpx.lib.node import as_internal_node
from mpx.componentry import class_implements
from mpx.componentry.interfaces import IPickles
from mpx.lib.neode.node import CompositeNode
from mpx.service.network.http.response import Response
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.lib.persistent import PersistentDataObject
from mpx.service.garbage_collector import GC_NEVER
from interfaces import IPeriodicDriverManager
from interfaces import IPeriodicDriver
from mpx.service.driver import ValueDriver

class DriverConfigurator(CompositeNode):
    LOADFAILURE = '"%s" failed to load %s "%s".  Exception follows.'

    def __init__(self, *args):
        self._pdo_lock = Lock()
        super(DriverConfigurator, self).__init__(*args)
    def configure(self, config):
        self.setattr('path', config.get('path','/driverconfig'))
        self.secured = as_boolean(as_internal_node("/services").secured)
        security_manager = config.get('security_manager',
                                      '/services/Security Manager')
        self.setattr('security_manager', security_manager)
        super(DriverConfigurator, self).configure(config)
    def configuration(self):
        config = super(DriverConfigurator, self).configuration()
        config['path'] = self.getattr('path')
        config['security_manager'] = self.getattr('security_manager')
        config['secured'] = str(self.getattr('secured'))
        return config
    def start(self):
        self.security_manager = self.nodespace.as_node(self.security_manager)
        self._pdo_lock.acquire()
        try:
            self._pdo = PersistentDataObject(self, dmtype=GC_NEVER)
            self._pdo.valuedrivers = {}
            self._pdo.load()
            valuedriverdumps = self._pdo.valuedrivers.items()
        finally: self._pdo_lock.release()
        super(DriverConfigurator, self).start()

        tstart = time.time()
        for drivername, driverdump in valuedriverdumps:
            try: IPickles(cPickle.loads(driverdump))()
            except:
                message = self.LOADFAILURE % (self.name, 'Value Driver', drivername)
                msglog.log('broadway', msglog.types.ERR, message)
                msglog.exception(prefix = 'Handled')
        tend = time.time()
        tlapse = tend - tstart
        msglog.log('broadway', msglog.types.INFO,
                   'Value Driver Configurator loaded '
                   '%s nodes in %s seconds.' % (len(valuedriverdumps), tlapse))
        return
    def stop(self):
        super(DriverConfigurator, self).stop()
    def match(self, path):
        return path.startswith(self.path)
    def _create_child(self, childtype, parent, config = {}):
        child = childtype()
        default = {'name': 'New %s 0' % childtype.__name__,
                   'parent': parent,
                   'source': 'DriverConfigurator',
                   'description': ''}
        default.update(config)
        count = 0
        while True:
            try: child.configure(default)
            except ValueError, error:
                # If failed over 20 times, assume error in logic and
                #   exit loop.  Also re-raise exception if name specified.
                if count > 20 or config.has_key('name'): raise
                else: count += 1
                suffix = ' %s' % count
                name = string.join(default['name'].split(' ')[0:-1], ' ')
                default['name'] =  name + suffix
            else: break
        return child

    def handle_request(self, request):
        response = Response(request)
        request_data = request.get_post_data_as_dictionary()
        request_data.update(request.get_query_string_as_dictionary())
        adapt = self.__handle_by_context(
           request_data.get('manage', ['/services/Value Drivers'])[0], request, request_data)
        webadapter = IWebContent(adapt)
        response.send(webadapter.render(self.path))
    
    def __as_node(self, url):
        managernode = self.nodespace.as_node(url)
        if self.secured:
            manager = self.security_manager.as_secured_node(url)
        else:
            manager = managernode
        return manager, managernode

    def __handle_by_context(self, context, request, data):
        node_url = urllib.unquote_plus(context)
        manager, managernode = self.__as_node(node_url)
        adapt = manager
        update_pdo = False
        if data.has_key('add'):
            childnode = None
            childconfig = {}
            # First check for 'edit' request, wherein a node is created iff 
            #   it does not exist.  The value of edit is the name of the child.
            if data.has_key('edit'):
                name = urllib.unquote_plus(data['edit'][0])
                if managernode.has_child(name):
                    childnode = managernode.get_child(name)
                childconfig['name'] = name
            # Testing Authorization by getting add_child function.
            if data.has_key('configure.name'):
                # Use setdefault to leave name untouched if already provided.
                childconfig.setdefault('name', urllib.unquote_plus(data['configure.name'][0]))
            if data.has_key('configure.input'):
                # Use setdefault to leave name untouched if already provided.
                childconfig.setdefault('input', urllib.unquote_plus(data['configure.input'][0]))
            if childnode is None:
                childnode = self._create_child(ValueDriver, managernode, childconfig)
                update_pdo = True
            adapt = childnode
        elif data.has_key('remove'):
            # Testing Authorization by getting remove_child.
            manager.remove_child
            name = urllib.unquote_plus(data['remove'][0])
            childnode = manager.get_child(name)
            childnode.prune()
            adapt = manager
            update_pdo = True
        elif data.has_key('configure'):
            name = urllib.unquote_plus(data['configure'][0])
            childnode = manager.get_child(name)
            # Testing Authorization by getting configure function.
            childnode.configure
            config = {}
            for attrname in data.keys():
                splitname = attrname.split('.')
                if len(splitname) == 2 and splitname[0] == 'configure':
                    values = map(urllib.unquote_plus, data[attrname])
                    if len(values) == 1: 
                        config[splitname[1]] = values[0]
                    else: 
                        config[splitname[1]] = values
            msglog.log('broadway', msglog.types.DB,
                       'Configuring "%s" with %s.' % (name, config))
            try: childnode.stop()
            except: msglog.exception(prefix = 'Handled')
            childnode.configure(config)
            try: childnode.start()
            except: msglog.exception(prefix = 'Handled')
            adapt = childnode
            update_pdo = True
        elif data.has_key('edit'):
            editing = data.get('edit')
            name = urllib.unquote_plus(editing[0])
            adapt = manager.get_child(name)
            update_pdo = False

        ##
        # Generic action handling for flexibility.
        action = None
        if data.has_key('actionName'):
            action = urllib.unquote_plus(data.get('actionName')[0])
        elif data.has_key('invocation'):
            action = urllib.unquote_plus(data.get('invocation')[0])

        if action is not None:
            if data.has_key('target'):
                target = urllib.unquote_plus(data.get('target')[0])
            elif data.has_key('edit'):
                target = urllib.unquote_plus(data['edit'][0])
            else:
                raise ValueError('Action must include either "target" or "edit" params.')

            params = map(urllib.unquote_plus, data.get('params', []))
            child = manager.get_child(target)
            method = getattr(child, action)
            result = method(*params)
            update_pdo = True
            print 'On %s: %s%s -> %s' % (target, action, params, result)
        # End Generic action handling.
        ##

        if update_pdo:
            pdodict = self._pdo.valuedrivers
            tstart = time.time()
            self._pdo_lock.acquire()
            try:
                pdodict.clear()
                children = managernode.children_nodes()
                for child in children:
                    pdodict[child.name] = cPickle.dumps(IPickles(child))
                self._pdo.save()
            finally: self._pdo_lock.release()
            tend = time.time()
            tlapse = tend - tstart
            message = 'Driver Configurator pickled and wrote '
            message += '%s nodes in %s seconds ' % (len(children), tlapse)
            message += 'for "%s".' % managernode.name
            msglog.log('broadway', msglog.types.INFO, message)
        
        if self.secured:
            adapt = self.security_manager.as_secured_node(adapt)
            adapt.test_adaptability()
        return adapt
    
    def debug_out(self, message):
        if not self.debug:
            msglog.log('DriverConfigurator', msglog.types.DB, message)
        return
