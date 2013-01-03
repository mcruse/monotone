"""
Copyright (C) 2007 2009 2010 2011 Cisco Systems

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
import os
import time
import string
import urllib
import cPickle
import itertools
from threading import Lock
from HTMLgen import HTMLgen
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import as_internal_node
from mpx.componentry.interfaces import IPickles
from mpx.lib.neode.node import CompositeNode
from mpx.service.network.http.response import Response
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.service.garbage_collector import GC_NEVER
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.persistence.datatypes import PersistentDictionary
from mpx.service.alarms2.trigger.triggers import Trigger
from mpx.service.alarms2.trigger.triggers import ComparisonTrigger
from mpx.service.alarms2.trigger.triggers import BoundTrigger
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation

def marshal(node):
    return cPickle.dumps(IPickles(node))

def unmarshal(dump):
    return IPickles(cPickle.loads(dump))()

class TriggersConfigurator(CompositeNode):
    security = SecurityInformation.from_default()
    secured_by(security)
    
    def __init__(self, *args):
        self._triggers = None
        self.security_manager = None
        self._pdo_lock = Lock()
        super(TriggersConfigurator, self).__init__(*args)
    def configure(self, config):
        self.setattr('path', config.get('path','/triggerconfig'))
        self.setattr('manager', config.get('container','/services/Trigger Manager'))
        self.secured = as_internal_node("/services").secured
        super(TriggersConfigurator, self).configure(config)
    def configuration(self):
        config = super(TriggersConfigurator, self).configuration()
        config['path'] = self.getattr('path')
        config['manager'] = self.getattr('manager')
        return config
    def start(self):
        filename = '%s (%s)' % (self.name, 'triggers')
        self.manager = self.nodespace.as_node(self.manager)
        self._pdo_lock.acquire()
        try:
            if self._triggers is None:
                self._triggers = PersistentDictionary(
                    filename, encode=None, decode=None)
            if not self._triggers:
                pdodata = PersistentDataObject(self, dmtype=GC_NEVER)
                if os.path.exists(pdodata.filename()):
                    msglog.log('broadway', msglog.types.INFO, 
                               "Migrating previous trigger data.")
                    pdodata.triggers = {}
                    pdodata.load()
                    self._triggers.update(pdodata.triggers)
                    pdodata.destroy()
                del(pdodata)
            self._loadtriggers()
            if self.secured:
                self.security_manager = self.as_node("/services/Security Manager")
            else:
                self.security_manager = None
        finally: 
            self._pdo_lock.release()
        return super(TriggersConfigurator, self).start()
    def stop(self):
        super(TriggersConfigurator, self).stop()
        self.manager = None
    def _loadtriggers(self, names=None):
        triggers = []
        if names is None:
            names = self._triggers.keys()
        elif not isinstance(names, (list, tuple, set)):
            names = [names]
        for name in names:
            dump = self._triggers[name]
            try:
                trigger = unmarshal(dump)
            except:
                msglog.log("broadway", msglog.types.WARN, 
                           "Unable to load trigger: %s" % name)
                msglog.exception(prefix="handled")
            else:
                triggers.append(trigger)
        return triggers
    def _storetriggers(self, triggers=None):
        if triggers is None:
            triggers = self.manager.get_triggers()
        elif not isinstance(triggers, (list, set, tuple)):
            triggers = [triggers]
        for trigger in triggers:
            try:
                dump = marshal(trigger)
            except:
                msglog.log("broadway", msglog.types.WARN, 
                           "Unable to marshal trigger: %s" % trigger.name)
                msglog.exception(prefix="handled")
            else:
                self._triggers[trigger.name] = dump
        return triggers
    def _poptriggers(self, names=None):
        if names is None:
            existing = set(self.manager.get_trigger_names())
            stored = self._triggers.keys()
            names = set(stored) - set(existing)
        elif not isinstance(names, (list, tuple, set)):
            names = [names]
        removed = []
        for name in names:
            try:
                self._triggers.pop(name)
            except:
                msglog.log("broadway", msglog.types.WARN, 
                           "Unable to remove trigger data: %s" % name)
                msglog.exception(prefix="handled")
            else:
                removed.append(name)
        return removed
    def match(self, path):
        return path.startswith(self.path)
    security.protect('create_trigger', 'Configure')
    security.protect('create_node', 'Configure')
    def create_trigger(self, name, config=()):
        config = dict(config)
        if "type" in config:
            type = config.pop("type")
        else:
            type = "ComparisonTrigger"
        if isinstance(type, str):
            if type.endswith("ComparisonTrigger"):
                type = ComparisonTrigger
            elif type.endswith("BoundTrigger"):
                type = BoundTrigger
            else:
                raise ValueError("Uknown type: %r" % type)
        config.setdefault("name", name)
        config.setdefault("parent", self.manager)
        trigger = self._create_trigger(type, config)
        self._storetriggers([trigger])
        return trigger.name
    create_node = create_trigger
    
    security.protect('remove_trigger', 'Configure')
    security.protect('remove_node', 'Configure')
    def remove_trigger(self, name):
        self._remove_trigger(name)
        self._poptriggers([name])
        return name
    remove_node = remove_trigger
    
    security.protect('configure_trigger', 'Configure')
    security.protect('configure_node', 'Configure')
    def configure_trigger(self, name=None, config=()):
        config = dict(config)
        if name is None:
            if config.has_key("name"):
                name = config["name"]
            else:
                raise TypeError("configure_trigger() requires"
                                " name or configuration with name")
        trigger = self.manager.get_trigger(name)
        try: 
            trigger.stop()
        except Exception, error:
            msglog.log('broadway', msglog.types.WARN,
                       'Ignoring following exception on stop.')
            msglog.exception(prefix = 'Handled')
        trigger.configure(config)
        try: 
            trigger.start()
        except Exception, error:
            msglog.log('broadway', msglog.types.WARN,
                       'Ignoring following exception on start.')
            msglog.exception(prefix = 'Handled')
        self._storetriggers([trigger])
        if name != trigger.name:
            self._poptriggers([name])
        return trigger.name
    configure_node = configure_trigger
    
    security.protect('get_trigger_names', 'View')
    security.protect('get_node_names', 'View')
    def get_trigger_names(self):
        return self.manager.children_names()
    get_node_names = get_trigger_names 
    
    security.protect('trigger_configuration', 'View')
    security.protect('node_configuration', 'View')   
    def trigger_configuration(self, name, extended=False):
        trigger = self.manager.get_trigger(name)
        config = trigger.configuration()
        if extended:
            config.setdefault("type", trigger.__class__.__name__)
        return config
    node_configuration = trigger_configuration
    def find_targets(self, extended=True):
        managers = [self._as_node("/services/Alarm Manager")]
        if extended:
            try:
                remote_managers = self._as_node("/services/Alarm Managers")
            except KeyError:
                msglog.warn("No Alarm Managers container defined.")
            else:
                managers.extend(remote_managers.children_nodes())
        targets = []
        for manager in managers:
            try:
                targets.extend(manager.children_nodes())
            except:
                msglog.warn("Unable to get targets from: %s." % manager)
                msglog.exception(prefix="handled")
        return map(as_node_url, targets)
    
    security.protect('trigger_targets', 'View')
    def trigger_targets(self, name):
        manager = self.manager
        if self.secured:
            manager = self.security_manager.as_secured_node(manager)
        trigger = manager.get_trigger(name)
        targets = []
        for target in trigger.get_targets(True):
            if not isinstance(target, str):
                target = as_node_url(target)
            targets.append(target)
        return targets
    
    security.protect('configure_targets', 'Configure')
    def configure_targets(self, name, targets):
        trigger = self.manager.get_trigger(name)
        existing = trigger.targets.copy()
        targets = set(targets)
        map(trigger.remove_target, existing - targets)
        map(trigger.add_target, targets - existing)
        self._storetriggers([trigger])
        return self.trigger_targets(name)
    def invoke(self, target, action, *args, **kw):
        trigger = self.manager.get_trigger(target)
        method = getattr(trigger, action)
        result = method(*params)
        self._storetriggers([trigger])
        return result
    def _create_trigger(self, type, config):
        manager = self.manager
        trigger = manager.nodespace.create_node(type)
        trigger.configure(config)
        return trigger
    def _remove_trigger(self, name):
        manager = self.manager
        if self.secured:
            manager = self.security_manager.as_secured_node(manager)
        trigger = manager.get_trigger(name)
        trigger.prune()
        
    def _as_node(self, nodeurl):
        if self.secured:
            return self.security_manager.as_secured_node(nodeurl)
        return as_node(nodeurl)
    def handle_request(self, request):
        update_pdo = False
        response = Response(request)
        request_data = request.get_post_data_as_dictionary()
        request_data.update(request.get_query_string_as_dictionary())
        if request_data.has_key('add'):
            name = self.create_trigger()
            adapt = self.manager.get_trigger(name)
        elif request_data.has_key('remove'):
            name = urllib.unquote_plus(request_data['remove'][0])
            self.remove_trigger(name)
            adapt = self.manager
        elif request_data.has_key('edit'):
            name = urllib.unquote_plus(request_data['edit'][0])
            adapt = self.manager.get_trigger(name)
        elif request_data.has_key('configure'):
            name = urllib.unquote_plus(request_data['configure'][0])
            trigger = self.manager.get_trigger(name)
            config = {}
            for attrname in request_data.keys():
                splitname = attrname.split('.')
                if len(splitname) == 2 and splitname[0] == 'configure':
                    value = urllib.unquote_plus(request_data[attrname][0])
                    config[splitname[1]] = value
            name = self.configure_trigger(config)
            adapt = self.manager.get_trigger(name)
        else: 
            adapt = self.manager
        if request_data.has_key('actionName'):
            action_target = urllib.unquote_plus(request_data.get('target')[0])
            action = urllib.unquote_plus(request_data.get('actionName')[0])
            params = map(urllib.unquote_plus, request_data.get('params'))
            self.invoke(action_target, action, *params)
        webadapter = IWebContent(adapt)
        response.send(webadapter.render())
