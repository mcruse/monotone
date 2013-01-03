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
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.configure import as_boolean
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.componentry import implements
from mpx.lib.neode.node import CompositeNode
from interfaces import IAlarmManager
from alarmevent import AlarmEvent
from alarmevent import ActionEvent
from alarmevent import StateEvent
from alarmevent import AlarmEventClosed
from alarm import Alarm
from mpx.lib.eventdispatch.dispatcher import Dispatcher
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation

class AlarmManager(CompositeNode):
    implements(IAlarmManager)
    security = SecurityInformation.from_default()
    secured_by(security)

    def __init__(self,*args,**kw):
        super(AlarmManager, self).__init__(*args, **kw)
        self.dispatcher = Dispatcher('Alarm Manager')
        self.cloud = None
        self.max_raised = 5
        self.max_cleared = 5
        self.max_accepted = 5
        self.use_https = False
        self.remote_events = {}
    security.protect('add_alarm', 'Configure')
    def add_alarm(self, alarm):
        self.add_child(alarm)
    security.protect('remove_alarm', 'Configure')
    def remove_alarm(self, name):
        self.get_alarm(name).prune()
    def get_alarm(self, name):
        return self.get_child(name)
    def get_alarms(self):
        return self.children_nodes()
    def get_alarm_names(self):
        return self.children_names()
    def get_alarm_dictionary(self):
        return self.children
    def get_remote_events(self):
        return self.remote_events.values()
    def get_local_events(self):
        events = []
        alarms = self.get_alarms()
        eventlists = map(Alarm.get_events, alarms)
        map(events.extend, eventlists)
        return events
    def get_all_events(self):
        return self.get_local_events() + self.get_remote_events()
    def get_event_dictionary(self, order_by = 'state', source = 'all'):
        try: events = getattr(self, 'get_' + source + '_events')()
        except AttributeError:
            raise ValueError('"%s" invalid value for source.' % source)
        eventdict = {}
        if order_by == 'state':
            for event in events:
                eventdict.setdefault(event.state, []).append(event)
        elif order_by == 'GUID' or order_by == 'guid':
            for event in events:
                eventdict[event.GUID] = event
        else:
            raise ValueError('"%s" invalid value for order_by' % order_by)
        return eventdict
    def get_events_by_state(self, state, source = 'all'):
        eventdict = self.get_event_dictionary('state', source)
        return eventdict.get(state.upper(), [])
    def handle_event_resend(self, cloudevent):
        self.message('Received Event Resend event %s' %(cloudevent))
        self.send_alarm_events_to_portal(cloudevent.origin)

    def send_alarm_events_to_portal(self,target):
        count = 0
        for alarm in self.get_alarms():
            for event in alarm.get_events():
                self.cloud.send_event_to_portal(event,['Alarm Manager'],target)
                count += 1
        self.message( 'Dispatched %s events because of Event Resend Request' % count)
        return count

    def handle_cloud_event(self, cloudevent):
        event = cloudevent()
    def dispatch(self, event, *args, **kw):
        result = self.dispatcher.timed_dispatch(event, *args, **kw)
        if isinstance(event, StateEvent):
            alarmevent = event.get_alarm_event()
            if alarmevent.is_local():
                self.cloud.handle_local_event(alarmevent, ['Alarm Manager'])
            else:
                guid = alarmevent.GUID
                if not self.remote_events.has_key(guid):
                    self.remote_events[guid] = alarmevent
                if isinstance(event, AlarmEventClosed):
                    del(self.remote_events[guid])
        return result
    def handle_cloud_change(self, event):
        count = 0
        for alarm in self.get_alarms():
            for event in alarm.get_events():
                self.cloud.handle_local_event(event, ['Alarm Manager'])
                count += 1
        self.message( 'Dispatched %s events because Cloud Change.' % count)
        self.dispatch(event)
        return count
    def register_for_type(self, *args, **kw):
        return self.dispatcher.register_for_type(*args, **kw)
    def configure(self, config):
        set_attribute(self, 'use_https', self.use_https, config, as_boolean)
        set_attribute(self, 'max_raised', 5, config, int)
        set_attribute(self, 'max_cleared', 5, config, int)
        set_attribute(self, 'max_accepted', 5, config, int)        
        return super(AlarmManager, self).configure(config)
    def configuration(self):
        config = super(AlarmManager, self).configuration()
        get_attribute(self, 'use_https', config, str)
        get_attribute(self, 'max_raised', config, str)
        get_attribute(self, 'max_cleared', config, str)
        get_attribute(self, 'max_accepted', config, str)
        return config
    def start(self):
        self.message('Alarm Manager starting.')
        server = self.nodespace.as_node('/services/network/http_server')
        if not server.is_enabled() or self.use_https:
            server = self.nodespace.as_node('/services/network/https_server')
        config = {'parent': server, 'enabled': 1,
                  'secured': True, 'debug': self.debug}
        syndic_handler_config = config.copy()
        config_handler_config = config.copy()
        cloud_handler_config = config.copy()
        cloud_config_handler_config = config.copy()
        exporter_handler_config = config.copy()
        trigger_handler_config = config.copy()
        syndic_handler_config['name'] = 'Syndication Viewer'
        syndic_handler_config['path'] = '/syndication'
        config_handler_config['name'] = 'Alarm Configurator'
        config_handler_config['path'] = '/alarmconfig'
        cloud_handler_config['name'] = 'Cloud Handler'
        cloud_handler_config['path'] = '/cloud'
        cloud_config_handler_config['name'] = 'Cloud Configurator'
        cloud_config_handler_config['path'] = '/cloudconfig'
        exporter_handler_config['name'] = 'Exporter Configurator'
        exporter_handler_config['path'] = '/exportconfig'
        trigger_handler_config['name'] = 'Trigger Configurator'
        trigger_handler_config['path'] = '/triggerconfig'

        ##
        # Frist create and setup Cloud Manager so events produced by
        #   startup of configurators can be propogated properly.
        startlist = []
        from mpx.service.cloud.manager import CloudManager
        cloud_manager = self.nodespace.create_node(CloudManager)
        cloud_manager.configure({'name': 'Cloud Manager',
                                 'parent': '/services',
                                 'debug': self.debug})
        self.cloud = cloud_manager
        startlist.append(cloud_manager)

        from mpx.service.cloud import request_handler
        cloud_handler_config['manager'] = '/services/Cloud Manager'
        cloud_handler = self.nodespace.create_node(request_handler.CloudHandler)
        cloud_handler.configure(cloud_handler_config)
        del request_handler
        startlist.insert(0, cloud_handler)

        from mpx.service.cloud.xhtml.configuration import request_handler
        cloud_config_handler_config['manager'] = '/services/Cloud Manager'
        cloud_config_handler = self.nodespace.create_node(request_handler.CloudConfigurator)
        cloud_config_handler.configure(cloud_config_handler_config)
        del request_handler
        startlist.append(cloud_config_handler)

        for cloudservice in startlist:
            cloudservice.start()
        self.message('Alarm Manager configured and started Cloud Manager, Handler, and Configurator.')

        ##
        # Syndication Handler is idempotent and so can be started anytime.
        from mpx.service.alarms2.presentation.syndication.http import request_handler
        syndic_handler = request_handler.SyndicationViewer()
        syndic_handler.configure(syndic_handler_config)
        del request_handler
        syndic_handler.start()
        self.message('Alarm Manager configured and started Syndication Handler.')

        ##
        # Startup Alarm Manager's configurator so that pickled Alarm Events may be
        #   recreated.
        from mpx.service.alarms2.presentation.xhtml.configuration import request_handler
        config_handler = self.nodespace.create_node(request_handler.AlarmConfigurator)
        config_handler.configure(config_handler_config)
        del request_handler
        config_handler.start()
        self.message('Alarm Manager created and started Alarm Configurator.')

        ##
        # Now that old Alarm Events have been recreated, configure and
        #   startup Exporters.
        from mpx.service.alarms2.export import exporter
        container = self.nodespace.create_node(exporter.ExporterContainer)
        container.configure({'name': 'Alarm Exporters',
                             'parent': '/services',
                             'debug': self.debug})
        export = self.nodespace.create_node(exporter.AlarmExporter)
        export.configure({'name': 'Alarm Logger',
                          'parent': container,
                          'debug': self.debug})
        formatter = self.nodespace.create_node(exporter.AlarmDictionaryFormatter)
        formatter.configure({'name': 'Log Formatter',
                             'parent': export,
                             'debug': self.debug})
        transporter = self.nodespace.create_node(exporter.LoggingTransporter)
        transporter.configure({'name': 'Alarm Logger',
                               'log': '/services/logger/Alarm Log',
                               'parent': export,
                               'debug': self.debug})
        export.add_source(self, StateEvent)
        container.start()
        self.message('Created and started alarm exporters and logger.')

        from mpx.service.alarms2.export.xhtml.configuration import request_handler
        export_config_handler = self.nodespace.create_node(request_handler.ExportersConfigurator)
        export_config_handler.configure(exporter_handler_config)
        del request_handler
        export_config_handler.start()
        self.message('Alarm Manager created and started Exporter Configurator.')


        self.cloud.add_listener(self.handle_cloud_event, 'Alarm Manager')
        self.cloud.add_listener(self.handle_event_resend, 'EventResend')
        from mpx.service.cloud.manager import FormationUpdated
        self.cloud.dispatcher.register_for_type(
            self.handle_cloud_change, FormationUpdated)
        self.message('Alarm Manager added itself as listender for Cloud Events.')


        ##
        # With all supporting infrastructure started, start triggers which may
        #   immediately generate alarms.
        from mpx.service.alarms2.trigger import triggermanager
        trigger_manager = self.nodespace.create_node(triggermanager.TriggerManager)
        trigger_manager.configure({'name': 'Trigger Manager',
                                   'parent': '/services',
                                   'debug': self.debug})
        del triggermanager
        trigger_manager.start()
        self.message('Alarm Manager created and started Trigger Manager.')

        from mpx.service.alarms2.trigger.xhtml.configuration import request_handler
        trigger_config_handler = self.nodespace.create_node(request_handler.TriggersConfigurator)
        trigger_config_handler.configure(trigger_handler_config)
        del request_handler
        self.message('Alarm Manager created and started Trigger Configurator.')
        trigger_config_handler.start()
        try:
            store = as_node("/services/Event Store")
        except KeyError:
            msglog.inform("Alarm Manager creating Event Store.")
            from mpx.service.alarms2 import store
            estore = store.EventStore()
            estore.configure({"name": "Event Store", "parent": "/services"})
            estore.start()
            msglog.inform("Alarm Manager setup and started Event Store.")
        else:
            msglog.inform("Alarm Manager found existing Event Store.")
        super(AlarmManager, self).start()
        self.message('Alarm Manager startup complete.')

    def message(self, message, mtype = msglog.types.INFO):
        if (mtype != msglog.types.DB) or self.debug:
            msglog.log('broadway', mtype, message)
        return
