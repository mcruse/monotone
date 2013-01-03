"""
Copyright (C) 2007 2008 2009 2010 2011 Cisco Systems

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
from mpx.lib.node import as_internal_node
from mpx.componentry.interfaces import IPickles
from mpx.lib.neode.node import CompositeNode
from mpx.service.network.http.response import Response
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.lib.persistent import PersistentDataObject
from mpx.service.garbage_collector import GC_NEVER
from mpx.service.alarms2.export.exporter import AlarmExporter
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation

class ExportersConfigurator(CompositeNode):
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self, *args):
        self._pdo_lock = Lock()
        self.manager = None
        super(ExportersConfigurator, self).__init__(*args)
    def configure(self, config):
        self.setattr('path', config.get('path','/exportconfig'))
        self.setattr('container', config.get('container','/services/Alarm Exporters'))
        self.secured = as_internal_node("/services").secured
        super(ExportersConfigurator, self).configure(config)
    def configuration(self):
        config = super(ExportersConfigurator, self).configuration()
        config['path'] = self.getattr('path')
        config['container'] = self.getattr('container')
        return config
    def start(self):
        self.container = self.nodespace.as_node(self.container)
        self._pdo_lock.acquire()
        try:
            self._pdo = PersistentDataObject(self, dmtype=GC_NEVER)
            self._pdo.exporters = {}
            self._pdo.load()
            exporterdumps = self._pdo.exporters.values()
        finally: 
            self._pdo_lock.release()
        super(ExportersConfigurator, self).start()
        tstart = time.time()
        for exporterdump in exporterdumps:
            IPickles(cPickle.loads(exporterdump))()
        tend = time.time()
        tlapse = tend - tstart
        msglog.log('broadway', msglog.types.INFO,
                   'Exporter Configurator loaded '
                   '%s exporters in %s seconds.' % (len(exporterdumps), tlapse))
        self.manager = self.container
    def stop(self):
        super(ExportersConfigurator, self).stop()
        self.container = None
    def match(self, path):
        return path.startswith(self.path)
    security.protect('create_node', 'Configure')
    def create_node(self, name, config=()):
        config = dict(config)
        config.setdefault("name", name)
        config.setdefault("parent", self.manager)
        exporter = self.manager.nodespace.create_node(AlarmExporter)
        exporter.configure(config)
        exporter.start()
        self.updatepdo()
        return exporter.name
    security.protect('remove_node', 'Configure')
    def remove_node(self, name):
        exporter = self.manager.get_child(name)
        exporter.prune()
        self.updatepdo()
        return exporter.name
    security.protect('configure_node', 'Configure')
    def configure_node(self, name, config):
        exporter = self.manager.get_child(name)
        exporter.configure(config)
        self.updatepdo()
        return exporter.name
    security.protect('node_configuration', 'View')
    def node_configuration(self, name, extended=False):
        exporter = self.manager.get_child(name)
        return exporter.configuration()
    security.protect('configure_formatter', 'Configure')
    def configure_formatter(self, exporter, config):
        return self.configure_node(exporter, {"formatter": config})
    security.protect('formatter_configuration', 'View')
    def formatter_configuration(self, exporter, extended=False):
        return self.node_configuration(exporter).get("formatter", {})
    security.protect('configure_transporter', 'Configure')
    def configure_transporter(self, exporter, config):
        return self.configure_node(exporter, {"transporter": config})
    security.protect('transporter_configuration', 'View')
    def transporter_configuration(self, exporter, extended=False):
        return self.node_configuration(exporter).get("transporter", {})
    security.protect('trigger_configuration', 'View')
    def trigger_configuration(self, name=None):
        manager = self.nodespace.as_node('/services/Alarm Manager')
        sources = [manager] + manager.get_alarms()
        configuration = dict([(source.url, []) for source in sources])
        if name:
            exporter = self.manager.get_child(name)
            configuration.update(exporter.trigger_configuration())
        configs = []
        for source,events in configuration.items():
            configs.append({"source": source, "events": events})
        return configs
    security.protect('configure_triggers', 'Configure')
    def configure_triggers(self, name, triggers=()):
        configuration = {}
        for config in triggers:
            configuration[config["source"]] = config["events"]
        exporter = self.manager.get_child(name)
        exporter.configure_triggers(configuration)
        self.updatepdo()
    security.protect('get_node_names', 'View')
    def get_node_names(self):
        return self.manager.children_names()
    def updatepdo(self):
        exporters = {}
        self._pdo_lock.acquire()
        try:
            for exporter in self.manager.get_exporters():
                exporters[exporter.name] = cPickle.dumps(IPickles(exporter))
            self._pdo.exporters = exporters
            self._pdo.save()
        finally: 
            self._pdo_lock.release()
    def handle_request(self, request):
        update_pdo = False
        response = Response(request)
        request_data = request.get_post_data_as_dictionary()
        request_data.update(request.get_query_string_as_dictionary())
        if request_data.has_key('add'):
            adapt = self.create_exporter("New Exporter")
        elif request_data.has_key('remove'):
            name = urllib.unquote_plus(request_data['remove'][0])
            self.remove_exporter(name)
            adapt = self.container
        elif request_data.has_key('edit'):
            name = urllib.unquote_plus(request_data['edit'][0])
            update_pdo = False
            adapt = self.container.get_exporter(name)
        elif request_data.has_key('configure'):
            name = urllib.unquote_plus(request_data['configure'][0])
            exporter = self.container.get_exporter(name)
            config = {'Exporter': {}, 'Formatter': {}, 'Transporter': {}}
            for attrname in request_data.keys():
                splitname = attrname.split('.')
                if len(splitname) == 2 and config.has_key(splitname[0]):
                    config[splitname[0]][splitname[1]] = urllib.unquote_plus(request_data[attrname][0])
            exportconfig = config['Exporter']
            exportconfig['formatter'] = config['Formatter']
            exportconfig['transporter'] = config['Transporter']
            exporter.configure(exportconfig)
            update_pdo = True
            adapt = exporter
        else: 
            adapt = self.container
        if request_data.has_key('actionName'):
            target = urllib.unquote_plus(request_data.get('target')[0])
            action = urllib.unquote_plus(request_data.get('actionName')[0])
            params = map(urllib.unquote_plus, request_data.get('params'))
            exporter = self.container.get_exporter(target)
            method = getattr(exporter, action)
            result = method(*params)
            update_pdo = True
        if update_pdo:
            self.updatepdo()
        webadapter = IWebContent(adapt)
        response.send(webadapter.render())
