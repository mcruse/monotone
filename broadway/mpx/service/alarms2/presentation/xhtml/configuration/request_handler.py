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
import os
import time
import string
import urllib
import cPickle
from threading import RLock
from threading import Event
from HTMLgen import HTMLgen
from mpx.lib import msglog
from mpx.lib.node import as_internal_node
from mpx.lib.configure import as_boolean
from mpx.service.alarms2.alarm import Alarm
from mpx.service.alarms2.alarmevent import StateEvent
from mpx.service.alarms2.alarmevent import AlarmEventClosed
from mpx.componentry.interfaces import IPickles
from mpx.lib.neode.node import CompositeNode
from mpx.service.network.http.response import Response
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.service.garbage_collector import GC_NEVER
from mpx.lib.persistence.datatypes import PersistentDictionary
from mpx.lib.persistent import PersistentDataObject

def compositetransformation(*transformations):
    """
        Return function which applies series of transformations
        on data based to function at call time.

        The first function provided should be the innermost
        function of the transformation.  So:

        f1(f2(f3(data))) -> compositetransformation(f3, f2, f1)(data)

        NOTE: closure is used to create composite-transformation.
    """
    def transform(data):
        for transformation in transformations:
            data = transformation(data)
        return data
    return transform

def migrate(pdo, decode):
    alarmpickles = pdo.alarms.values()
    eventpickles = pdo.events.values()
    for alarmpickle in alarmpickles:
        decode(alarmpickle)
    for eventpickle in eventpickles:
        decode(eventpickle)

class AlarmConfigurator(CompositeNode):
    def __init__(self, *args):
        self.running = Event()
        self.synclock = RLock()
        self.secured = True
        self.alarms = None
        self.events = None
        self.managernode = None
        self.path = '/alarmconfig'
        self.securitymanager = None
        self.manager = '/services/Alarm Manager'
        super(AlarmConfigurator, self).__init__(*args)
    def as_node(self, nodeurl):
        return self.nodespace.as_node(nodeurl)
    def as_secured_node(self, node):
        return self.securitymanager.as_secured_node(node)
    def as_appropriate_node(self, nodeurl):
        node = self.as_node(nodeurl)
        if self.secure:
            node = self.as_secured_node(node)
        return node
    def configure(self, config):
        self.path = config.get('path', self.path)
        self.manager = config.get('manager', self.manager)
        self.secured = getattr(as_internal_node("/services"), "secured", 1)
        super(AlarmConfigurator, self).configure(config)
    def configuration(self):
        config = super(AlarmConfigurator, self).configuration()
        config['path'] = self.path
        config['manager'] = self.manager
        config['secured'] = str(int(self.secured))
        return config
    def encode(self, obj):
        return cPickle.dumps(IPickles(obj))
    def decode(self, data):
        state = cPickle.loads(data)
        decoder = IPickles(state)
        try:
            obj = decoder(True)
        except:
            message = "Decoder %s failed to decode state: %r."
            msglog.warn(message % (decoder, state))
            msglog.exception()
            raise
        return obj
    def start(self):
        self.managernode = self.as_node(self.manager)
        self.synclock.acquire()
        try:
            alarmsname = '%s (%s)' % (self.name, 'alarms')
            eventsname = '%s (%s)' % (self.name, 'events')
            self.alarms = PersistentDictionary(alarmsname,
                                               encode=self.encode,
                                               decode=self.decode)
            self.events = PersistentDictionary(eventsname,
                                               encode=self.encode,
                                               decode=self.decode)
            # Migrate PDO data from old style persistence.
            pdodata = PersistentDataObject(self, dmtype=GC_NEVER)
            if os.path.exists(pdodata.filename()):
                msglog.log('broadway', msglog.types.INFO,
                           "Migrating previous alarm and event data")
                pdodata.events = {}
                pdodata.alarms = {}
                pdodata.load()
                migrate(pdodata, self.decode)
                self.rebuildstorage()
                pdodata.destroy()
            del(pdodata)
        finally:
            self.synclock.release()
        self.securitymanager = self.as_node('/services/Security Manager')
        
        register = self.managernode.register_for_type
        self.sub = register(self.handle_event, StateEvent)
        self.running.set()
        super(AlarmConfigurator, self).start()
    def stop(self):
        self.running.clear()
        super(AlarmConfigurator, self).stop()
        self.managernode = None
        self.securitymanager = None
    def match(self, path):
        return path.startswith(self.path)
    def is_running(self):
        return self.running.isSet()
    def create_node(self, name, config=(), secure=True, persist=True):
        config = dict(config)
        config["name"] = name
        return self.create_alarm(config, secure, persist).as_node_url()
    def create_alarm(self, config=(), secure=1, persist=False):
        config = dict(config)
        manager = self.managernode
        if self.secured and secure:
            manager = self.securitymanager.as_secured_node(manager)
        # Silly little statement to validate adding before creating.
        add_alarm = manager.add_alarm
        alarm = self.managernode.nodespace.create_node(Alarm)
        default = {'name': 'New Alarm 0',
                   'parent': '/services/Alarm Manager',
                   'description': '', 'priority': 'P1', 'source': self.name}
        default.update(config)
        count = 0
        while True:
            try:
                alarm.configure(default)
            except ValueError, error:
                # If failed over 20 times, assume error in logic and
                #   exit loop.  Also re-raise exception if name specified.
                if count > 20 or config.has_key('name'):
                    raise
                else:
                    count += 1
                suffix = ' %s' % count
                name = string.join(default['name'].split(' ')[0:-1], ' ')
                default['name'] =  name + suffix
            else:
                break
        alarm.start()
        if persist:
            self.synclock.acquire()
            try:
                alarmnode = self.managernode.get_alarm(alarm.name)
                self.alarms[alarmnode.name] = alarmnode
            finally:
                self.synclock.release()
        return alarm
    def configure_alarm(self, name, config, secure=True, **kw):
        alarmnode = self.managernode.get_alarm(name)
        if self.secured and secure:
            alarm = self.as_secured_node(alarmnode)
        else:
            alarm = alarmnode
        self.synclock.acquire()
        try:
            alarm.configure(config)
            if name in self.alarms:
                self.alarms[alarmnode.name] = alarmnode
                if name != alarmnode.name:
                    self.alarms.pop(name)
        finally:
            self.synclock.release()
        return alarm.as_node_url()
    def remove_alarm(self, name, secure=True, **kw):
        alarmnode = self.managernode.get_alarm(name)
        if self.secured and secure:
            alarm = self.as_secured_node(alarmnode)
        else:
            alarm = alarmnode
        alarmurl = alarmnode.as_node_url()
        self.synclock.acquire()
        try:
            alarm.prune()
            if name in self.alarms:
                self.alarms.pop(name)
        finally:
            self.synclock.release()
        return alarmurl
    def trigger_alarm(self, name):
        alarm = self.managernode.get_alarm(name)
        if self.secured:
            alarm = self.as_secured_node(alarm)
        users = self.securitymanager.user_manager
        username = users.user_from_current_thread().name
        alarm.trigger(self, time.time(), 'Test triggered by: %r' % username)
        return alarm.get_event_counts()
    def clear_alarm(self, name):
        alarm = self.managernode.get_alarm(name)
        if self.secured:
            alarm = self.as_secured_node(alarm)
        users = self.securitymanager.user_manager
        username = users.user_from_current_thread().name
        alarm.clear(self, time.time(), 'Test cleared by: %r' % username)
        return alarm.get_event_counts()
    def get_alarm_names(self):
        return list(sorted(self.managernode.get_alarm_names()))
    def get_alarm_configuration(self, name):
        alarm = self.managernode.get_alarm(name)
        if self.secured:
            alarm = self.as_secured_node(alarm)
        configuration = alarm.configuration()
        configuration["counts"] = alarm.get_event_counts()
        configuration.pop("parent")
        return configuration
    def get_alarm_configurations(self, names=None):
        if names is None:
            names = self.get_alarm_names()
        return [self.get_alarm_configuration(name) for name in names]
    def get_event_counts(self, name):
        alarm = self.managernode.get_alarm(name)
        if self.secured:
            alarm = self.as_secured_node(alarm)
        return alarm.get_event_counts()
    def handle_request(self, request):
        update_pdo = False
        storage = None
        response = Response(request)
        username = request.user_object().name()
        request_data = request.get_post_data_as_dictionary()
        request_data.update(request.get_query_string_as_dictionary())
        if request_data.has_key('add'):
            self.synclock.acquire()
            try:
                alarm = self.create_alarm()
                #CSCte94335 - commenting following because it is temporary alarm
                #self.alarms[alarm.name] = alarm
            finally:
                self.synclock.release()
            adapt = alarm
            if self.debug:
                message = "%s.handle_request() handling add request"
                msglog.log("broadway", msglog.types.DB, message % self.name)
        elif request_data.has_key('remove'):
            self.remove_alarm(urllib.unquote_plus(request_data['remove'][0]))
            adapt = self.managernode
            if self.debug:
                message = "%s.handle_request() handling remove request"
                msglog.log("broadway", msglog.types.DB, message % self.name)
        elif request_data.has_key('edit'):
            name = urllib.unquote_plus(request_data['edit'][0])
            adapt = self.managernode.get_child(name)
            if self.debug:
                message = "%s.handle_request() handling edit request"
                msglog.log("broadway", msglog.types.DB, message % self.name)
        elif request_data.has_key('configure'):
            name = urllib.unquote_plus(request_data['configure'][0])
            # CSCte94335 - if old alarm name does not exist then add this alarm condition
            # else update the existing alarm
            if self.alarms.get(name) == None:
                # create a new alarm
                config = {}
                # CSCte94370 - strip the name string to ignore spaces.
                config['name'] = urllib.unquote_plus(
                    request_data.get('name')[0]).strip()
                config['priority'] = urllib.unquote_plus(
                    request_data.get('priority')[0])
                config['description'] = urllib.unquote_plus(
                    request_data.get('description')[0])
                config['parent'] = urllib.unquote_plus(
                    request_data.get('parent')[0])
                config['max_raised'] = urllib.unquote_plus(
                    request_data.get('max_raised')[0])
                config['max_cleared'] = urllib.unquote_plus(
                    request_data.get('max_cleared')[0])
                config['max_accepted'] = urllib.unquote_plus(
                    request_data.get('max_accepted')[0])
                self.create_alarm(config, persist=True)
            else:
                alarmnode = self.alarms[name]
                if self.secured:
                    alarm = self.as_secured_node(alarmnode)
                else:
                    alarm = alarmnode
                config = {}
                # CSCte94370 - strip the name string to ignore spaces.
                config['name'] = urllib.unquote_plus(
                    request_data.get('name', [alarm.name])[0]).strip()
                config['priority'] = urllib.unquote_plus(
                    request_data.get('priority', [alarm.priority])[0])
                config['description'] = urllib.unquote_plus(
                    request_data.get('description', [alarm.description])[0])
                config['parent'] = urllib.unquote_plus(
                    request_data.get('parent', [alarm.parent])[0])
                config['max_raised'] = urllib.unquote_plus(
                    request_data.get('max_raised', [alarm.max_raised])[0])
                config['max_cleared'] = urllib.unquote_plus(
                    request_data.get('max_cleared', [alarm.max_cleared])[0])
                config['max_accepted'] = urllib.unquote_plus(
                    request_data.get('max_accepted', [alarm.max_accepted])[0])
                self.configure_alarm(name, config)
            adapt = self.managernode
            if self.debug:
                message = "%s.handle_request() handling edit request"
                msglog.log("broadway", msglog.types.DB, message % self.name)
        else:
            if request_data.has_key('trigger'):
                name = urllib.unquote_plus(request_data['trigger'][0])
                self.trigger_alarm(name)
            elif request_data.has_key('clear'):
                name = urllib.unquote_plus(request_data['clear'][0])
                self.clear_alarm(name)
            adapt = self.managernode
        if self.secured:
            adapt = self.securitymanager.as_secured_node(adapt)
            # Throw authorization error if adaptation will fail.
            adapt.test_adaptability()
        webadapter = IWebContent(adapt)
        request['Content-Type'] = "text/html"
        html = webadapter.render()
        #CSCte94335 - deleting the alarm that was created temporarily during 'add'
        if request_data.has_key('add'):
            self.synclock.acquire()
            try:
                adapt.prune()
            finally:
                self.synclock.release()
        if self.debug:
            message = ("%s.handle_request() handling "
                       "adapting %s returning: \n\r%s\n\r")
            msglog.log("broadway", msglog.types.DB,
                       message % (self.name, adapt, html))
        response.send(html)
    def handle_event(self, event):
        if event.is_local():
            alarmevent = event.get_alarm_event()
            tstart = time.time()
            self.synclock.acquire()
            try:
                if isinstance(event, AlarmEventClosed):
                    try:
                        del(self.events[alarmevent.GUID])
                    except KeyError:
                        pass
                else:
                    self.events[alarmevent.GUID] = alarmevent
            finally:
                self.synclock.release()
    def rebuildstorage(self):
        self.synclock.acquire()
        try:
            # Clear alarm data and rebuild from nodes.
            alarms = self.managernode.get_alarms()
            backup = self.alarms.copy()
            self.alarms.clear()
            try:
                self.alarms.update([(alarm.name, alarm) for alarm in alarms])
            except:
                msglog.log('broadway', msglog.types.ERR,
                           "Rebuild of alarm configuration data failed.")
                self.alarms.clear()
                self.alarms.update(backup)
                msglog.log('broadway', msglog.types.WARN,
                           "Alarm configuration data has been rolled back.")
                raise
            else:
                msglog.log('broadway', msglog.types.INFO,
                           "Alarm configuration data rebuilt.")
            # Clear event data and rebuild from alarms.
            events = []
            for alarm in alarms:
                events.extend(alarm.get_events())
            backup = self.events.copy()
            self.events.clear()
            try:
                self.events.update([(ev.GUID, ev) for ev in events])
            except:
                msglog.log('broadway', msglog.types.ERR,
                           "Rebuild of alarm event data failed.")
                self.events.clear()
                self.events.update(backup)
                msglog.log('broadway', msglog.types.WARN,
                           "Alarm event data has been rolled back.")
                raise
            else:
                msglog.log('broadway', msglog.types.INFO,
                           "Alarm event data rebuilt.")

        except:
            msglog.log('broadway', msglog.types.INFO,
                       "Alarm and event data rebuild failed.")
            msglog.exception(prefix="handled")
        else:
            msglog.log('broadway', msglog.types.INFO,
                       "Alarm and event data rebuild complete.")
        finally:
            self.synclock.release()
