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
import cgi
import time
import string
import urllib
import cPickle
from threading import Lock
from HTMLgen import HTMLgen
from mpx.lib import msglog
from mpx.lib.node import as_node_url, as_internal_node
from mpx.lib.configure import as_boolean
from mpx.componentry import class_implements
from mpx.componentry.interfaces import IPickles
from mpx.lib.neode.node import CompositeNode
from mpx.service.network.http.response import Response
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.persistence.datatypes import PersistentDictionary
from mpx.lib.exceptions import ENameInUse
from mpx.service.garbage_collector import GC_NEVER
from interfaces import ISchedule
from interfaces import IScheduleHolder
from interfaces import IScheduleHolderParent
from scheduler import Schedules as ScheduleHolder
from scheduler import Scheduler as Schedule

class ScheduleConfigurator(CompositeNode):
    LOADFAILURE = '"%s" failed to load %s "%s".  Exception follows.'

    def __init__(self, *args):
        self._pdo = None
        self.template = ""
        self._pdo_lock = Lock()
        self.page_template = "/templates/schedules.html"        
        super(ScheduleConfigurator, self).__init__(*args)
    def configure(self, config):
        self.setattr('path', config.get('path','/scheduleconfig'))
        self.secured = as_boolean(as_internal_node("/services").secured)
        security_manager = config.get('security_manager',
                                      '/services/Security Manager')
        self.setattr('security_manager', security_manager)
        super(ScheduleConfigurator, self).configure(config)
    def configuration(self):
        config = super(ScheduleConfigurator, self).configuration()
        config['path'] = self.getattr('path')
        config['security_manager'] = self.getattr('security_manager')
        config['secured'] = str(self.getattr('secured'))
        return config
    def start(self):
        self.nodes = []
        from mpx.service.time.time_zone import TimeZone
        if not IScheduleHolderParent.implementedBy(TimeZone):
            class_implements(TimeZone, IScheduleHolderParent)
        self.security_manager = self.nodespace.as_node(self.security_manager)
        self._pdo_lock.acquire()
        try:
            if not self._pdo:
                self._pdo = PersistentDataObject(self, dmtype=GC_NEVER)
                self._pdo.holders = {}
                self._pdo.schedules = {}
                self._pdo.load()
            holderdicts = self._pdo.holders.values()
            holderdumps = []
            for holderdict in holderdicts:
                holderdumps.extend(holderdict.items())
            # schedules = {'local': {'Holder1': {'Sched1': Sched1Dump}, 'Holder2': ...}, 'UTC': ...}
            scheduledicts = []
            [scheduledicts.extend(holderdict.values()) 
             for holderdict in self._pdo.schedules.values()]
            scheduledumps = []
            for scheduledict in scheduledicts:
                scheduledumps.extend(scheduledict.items())
        finally: 
            self._pdo_lock.release()
        super(ScheduleConfigurator, self).start()
        tstart = time.time()
        for holdername, holderdump in holderdumps:
            try: 
                self.nodes.append(IPickles(cPickle.loads(holderdump))())
            except:
                message = self.LOADFAILURE % (self.name, 'Schedule Holder', holdername)
                msglog.log('broadway', msglog.types.ERR, message)
                msglog.exception(prefix = 'Handled')
        tend = time.time()
        tlapse = tend - tstart
        msglog.log('broadway', msglog.types.INFO,
                   'Schedule Configurator loaded '
                   '%s nodes in %s seconds.' % (len(holderdumps), tlapse))
        
        tstart = time.time()
        for schedulename, scheduledump in scheduledumps:
            try: self.nodes.append(IPickles(cPickle.loads(scheduledump))())
            except:
                message = self.LOADFAILURE % (self.name, 'Schedule Holder', schedulename)
                msglog.log('broadway', msglog.types.ERR, message)
                msglog.exception(prefix = 'Handled')
        tend = time.time()
        tlapse = tend - tstart
        msglog.log('broadway', msglog.types.INFO,
                   'Schedule Configurator loaded '
                   '%s nodes in %s seconds.' % (len(scheduledumps), tlapse))
        self.template = self.parent.read_resource(self.page_template)
    def stop(self):
        super(ScheduleConfigurator, self).stop()
    def match(self, path):
        return path.startswith(self.path)
    def message(self, message, *args, **kw):
        mtype = kw.get("type", msglog.types.INFO)
        if mtype != msglog.types.DB or self.debug:
            message = message % args
            msglog.log("broadway", mtype, "[%s] %s" % (self.name, message))
            return True
        return False
    def debugout(self, *args, **kw):
        kw.setdefault("type", msglog.types.DB)
        return self.message(*args, **kw)
    def configurenode(self, node, data):
        config = {}
        for fieldname in data.keys():
            prefix,sep,attrname = fieldname.partition('.')
            if sep and prefix == "configure":
                values = map(urllib.unquote_plus, data[fieldname])
                if (attrname == "name"):
                    #make sure the node name starts with RZSched_
                    #if not, append it.
                    if not values[0].startswith("RZSched_"):
                        values[0] = "RZSched_" + values[0]
                config[attrname] = values[0]
        self.message("configuring %s with %s", node, config)
        try: 
            node.stop()
        except: 
            msglog.exception(prefix='Handled')
        node.configure(config)
        try: 
            node.start()
        except: 
            msglog.exception(prefix='Handled')
        return node.parent
    def createnode(self, node, data):
        if IScheduleHolderParent.providedBy(node):
            defaultname = "Holder %d"
            nodetype = ScheduleHolder
        elif IScheduleHolder.providedBy(node):
            defaultname = "RZShed_%d"
            nodetype = Schedule
        else:
            message = "createnode() does not know what to create for %s"
            raise TypeError(message % node)
        parentnode = node
        if data.has_key("configure.name"):
            childname = urllib.unquote_plus(data['configure.name'][0])
        else:
            index = len(parentnode.children_nodes()) + 1
            childname = defaultname % index
            while parentnode.has_child(childname):
                index += 1
                childname = defaultname % index
            childname = defaultname % len(parentnode.children_nodes())
        if not childname:
            raise TypeError("Illegal node name: %r" % childname)
        if IScheduleHolder.providedBy(node):
            if childname == '':
                error = "Holder name required"
                raise TypeError(error)
            if not childname.startswith("RZSched_"):
                if childname.lower().startswith("rzsched_"):
                    childname = childname.lower().split("rzsched_")[1]
                childname = "RZSched_" + childname                
        config = {'name': childname, 'parent': parentnode,
                   'description': '', 'source': 'ScheduleConfigurator'}
        message = "createnode() creating %s type child of %s."
        self.message(message, nodetype.__name__, parentnode)
        childnode = nodetype()
        childnode.configure(config)
        return parentnode
    def holder_parents(self):
        children = as_node("/services/time").children_nodes()
        return filter(IScheduleHolderParent.providedBy, children)
    def holder_parent_names(self):
        return [parent.name for parent in self.holder_parents()]
    def schedule_holders(self, parent=None):
        if parent is None:
            parent = self.nodespace.as_node("/services/time/local")
        return filter(IScheduleHolder.providedBy, parent.children_nodes())
    def schedule_holder_names(self, parent=None):
        return [holder.name for holder in self.schedule_holders(parent)]
    def prunenode(self, node, data):
        self.message("removing %s", as_node_url(node))
        parentnode = node.parent
        self.debugout("parent node %s", as_node_url(parentnode))
        node.prune()
        return parentnode        
    def handle_request(self, request):
        response = Response(request)
        data = request.get_post_data_as_dictionary()
        data.update(request.get_query_string_as_dictionary())
        if data.has_key("node"):
            nodeurl = urllib.unquote_plus(data["node"][0])
        else:
            nodeurl = "/services/time/local"
        try:
            adapt = self.__handle_by_context(nodeurl, request, data)
        except TypeError, error:
            msglog.exception(prefix="handled")
            response.send_error(500, str(error))
        else:
            webadapter = IWebContent(adapt)
            content = webadapter.render(self.path)
            response.send(content)
    def __as_node(self, url):
        managernode = self.nodespace.as_node(url)
        if self.secured:
            manager = self.security_manager.as_secured_node(url)
        else:
            manager = managernode
        return manager, managernode
    def __handle_by_context(self, nodeurl, request, data):
        node,insecurenode = self.__as_node(nodeurl)
        adapt = node
        updatepdo = False
        self.debugout("handle_by_context(%r, %r, %r)", nodeurl, request, data)
        if data.has_key("actionName"):
            # Action may be any method exposed by the context 
            # node, or it may be one of the "special" actions 
            # whose meaning is provided by the request-handler.
            # Special actions include creating nodes, pruning 
            # child nodes, and configuring a node.
            action = urllib.unquote_plus(data["actionName"][0])
            if action == "configure":
                updatepdo = True
                adapt = self.configurenode(node, data)
            elif action == "prune" or action == "remove":
                updatepdo = True
                adapt = node = self.prunenode(node, data)
            elif action == "create" or action == "add":
                updatepdo = True
                adapt = self.createnode(node, data)
            elif action == "invoke":
                updatepdo = True
                if not data.has_key("methodName"):
                    raise TypeError("invoke action require 'methodName'")
                methodname = urllib.unquote_plus(data["methodName"])
                params = map(urllib.unquote_plus, data.get('params', []))
                method = getattr(node, methodname)
                self.message("invoking %s.%s(%r)", node, methodname, params)
                result = method(*params)
                adapt = node
            elif action not in ("schedules", "edit", "rename"):
                raise TypeError("action not recognized: %s" % action)
        else:
            adapt = node
            updatepdo = False
        if updatepdo:
            self.updatepdo(node)
        if self.secured:
            adapt = self.security_manager.as_secured_node(adapt)
            adapt.test_adaptability()
        return adapt
    def scheduler_holder_names(self, url=None):
        if url is None:
            url = "/services/time/local"
        self.security_manager.as_secured_node(url)
    def updatepdo(self, managernode):
        self.debugout("updatepdo(%s)", as_node_url(managernode))
        tstart = time.time()
        while not IScheduleHolderParent.providedBy(managernode):
            managernode = managernode.parent
        managername = managernode.name
        self.message('updating PDO for %s.', as_node_url(managernode))
        self._pdo_lock.acquire()
        try: 
            holderdict = self._pdo.holders.setdefault(managername, {})
            holderdict.clear()
            scheduledicts = self._pdo.schedules.setdefault(managername,{})
            scheduledicts.clear()
            children = managernode.children_nodes()
            holders = filter(IScheduleHolder.providedBy, children)
            for holder in holders:
                if holder.source == 'ScheduleConfigurator':
                    self.debugout('storing holder %s.', as_node_url(holder))
                    holderdict[holder.name] = cPickle.dumps(IPickles(holder))
                else:
                    self.debugout('skipping holder %s.', as_node_url(holder))
                scheduledict = scheduledicts.setdefault(holder.name, {})
                scheduledict.clear()
                schedules = filter(ISchedule.providedBy, 
                                   holder.children_nodes())
                for schedule in schedules:
                    if schedule.source == 'ScheduleConfigurator':
                        self.debugout(
                            'storing schedule %s.', as_node_url(schedule))
                        scheduledata = cPickle.dumps(IPickles(schedule))
                        scheduledict[schedule.name] = scheduledata
                    else:
                        self.debugout(
                            'skipping schedule %s.', as_node_url(schedule))
            self._pdo.save()
        finally: 
            self._pdo_lock.release()
        tend = time.time()
        self.debugout('took %0.3f secs to update PDO.', tend - tstart)         
