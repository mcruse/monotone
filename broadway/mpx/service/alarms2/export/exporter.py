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
import time
import weakref
import types
from StringIO import StringIO
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.configure import as_boolean
from mpx.lib.exceptions import MpxException
from mpx.lib.sgml_formatter import SGMLFormatter
from mpx.componentry import implements
from mpx.service.alarms2.alarmevent import StateEvent
from mpx.service.alarms2.alarmevent import AlarmEventRaised
from mpx.service.alarms2.alarmevent import AlarmEventAccepted
from mpx.service.alarms2.alarmevent import AlarmEventCleared
from mpx.service.alarms2.alarmevent import AlarmEventClosed
from mpx.service.alarms2.export.interfaces import IAlarmExporter
from mpx.service.alarms2.export.interfaces import IExporterContainer
from mpx.service.alarms2.export.interfaces import IAlarmFormatter
from mpx.service.alarms2.export.interfaces import ITransporter
from mpx.lib.neode.node import CompositeNode

eventnames = ['all', 'raised', 'accepted', 'cleared', 'closed']
eventlookup = {'all': StateEvent,
               StateEvent: StateEvent,
               'raised': AlarmEventRaised,
               AlarmEventRaised: AlarmEventRaised,
               'accepted': AlarmEventAccepted,
               AlarmEventAccepted: AlarmEventAccepted,
               'cleared': AlarmEventCleared,
               AlarmEventCleared: AlarmEventCleared,
               'closed': AlarmEventClosed,
               AlarmEventClosed: AlarmEventClosed}

eventnamelookup = {}
for name in eventnames:
    event = eventlookup[name]
    eventnamelookup[event] = name

class ExporterContainer(CompositeNode):
    implements(IExporterContainer)
    def get_exporters(self):
        return self.children_nodes()
    def get_exporter(self, name):
        return self.get_child(name)
    def remove_exporter(self, exporter):
        return self.prune_child(exporter)
    def get_exporter_names(self):
        return self.children_names()
    def add_exporter(self, exporter):
        if not IAlarmExporter.providedBy(exporter):
            raise TypeError('Exporter must implement IAlarmExporter.')
        return self.add_child(exporter)

from mpx.service.data import smtp_transporter
class SMTPTransporter(CompositeNode, smtp_transporter.SMTPTransporter):
    implements(ITransporter)
    def __init__(self, *args):
        CompositeNode.__init__(self, *args)
        smtp_transporter.SMTPTransporter.__init__(self)
    def configure(self, config):
        config.setdefault('subtype', 'html')
        smtp_transporter.SMTPTransporter.configure(self, config)
        self.setattr('transport_type', 'smtp')
        CompositeNode.configure(self, config)
    def configuration(self):
        config = smtp_transporter.SMTPTransporter.configuration(self)
        config.update(CompositeNode.configuration(self))
        for attrname in ['debug','host','port','authenticate','username',
                         'password','sender','recipients','subject',
                         'timeout','custom_domain','subtype','as_attachment']:
            config.setdefault(attrname,'')
        config['transport_type'] = self.getattr('transport_type')
        return config
    def is_setup(self):
        return (hasattr(self, 'host') and hasattr(self, 'recipients') and
                len(self.host.strip()) and len(self.recipients))

ftp_attrs = \
['host', 'port', 'directory', 'username', 'password', 'timeout', 
'file_prefix', 'file_suffix', 'name_scheme', 'timestamp_format', 
'passive_mode','file_append']
from mpx.service.data.ftptransport import standard
class FTPTransporter(CompositeNode, standard.FTPTransporter):
    implements(ITransporter)
    def __init__(self, *args):
        CompositeNode.__init__(self, *args)
        standard.FTPTransporter.__init__(self)
    def configure(self, config):
        standard.FTPTransporter.configure(self, config)
        self.setattr('transport_type', 'ftp')
        CompositeNode.configure(self, config)
    def configuration(self):
        config = standard.FTPTransporter.configuration(self)
        config.update(CompositeNode.configuration(self))
        for attrname in ftp_attrs:
            config.setdefault(attrname, '')
        config['transport_type'] = self.getattr('transport_type')
        return config
    def is_setup(self):
        return (hasattr(self, 'host') and hasattr(self, 'username') and
                hasattr(self, 'password'))
        
from mpx.service.data.ftptransport import secure
class SFTPTransporter(CompositeNode, secure.SFTPTransporter):
    implements(ITransporter)
    def __init__(self, *args):
        CompositeNode.__init__(self, *args)
        secure.SFTPTransporter.__init__(self)
    def configure(self, config):
        secure.SFTPTransporter.configure(self, config)
        self.setattr('transport_type', 'sftp')
        CompositeNode.configure(self, config)
    def configuration(self):
        config = secure.SFTPTransporter.configuration(self)
        config.update(CompositeNode.configuration(self))
        for attrname in ftp_attrs:
            config.setdefault(attrname, '')
        config['transport_type'] = self.getattr('transport_type')
        return config
    def is_setup(self):
        return (hasattr(self, 'host') and hasattr(self, 'username') and
                hasattr(self, 'password'))

from mpx.service.data import http_post_transporter
class HTTPPostTransporter(CompositeNode, 
                          http_post_transporter.HTTPPostTransporter):
    implements(ITransporter)
    def __init__(self, *args):
        CompositeNode.__init__(self, *args)
        http_post_transporter.HTTPPostTransporter.__init__(self)
    def configure(self, config):
        http_post_transporter.HTTPPostTransporter.configure(self, config)
        self.setattr('transport_type', 'http-post')
        CompositeNode.configure(self, config)
    def configuration(self):
        config = http_post_transporter.HTTPPostTransporter.configuration(self)
        config.update(CompositeNode.configuration(self))
        for attrname in ['post_url', 'chunked_data', 'debug', 'content_type',
                         'timeout', 'user', 'password']:
            config.setdefault(attrname, '')
        config['transport_type'] = self.getattr('transport_type')
        return config
    def is_setup(self):
        return hasattr(self, 'post_url')
            
class _AlarmFormatter(CompositeNode):
    implements(IAlarmFormatter)
    gmt_format = '%a, %d %b %Y %H:%M:%S +0000'
    local_format = '%a, %d %b %Y %H:%M:%S %Z'
    def is_setup(self): 
        return True
    def datetime(self, timestamp):
        if self.parent.gm_time:
            timestruct = time.gmtime(timestamp)
            datetime = time.strftime(self.gmt_format, timestruct)
        else:
            timestruct = time.localtime(timestamp)
            datetime = time.strftime(self.local_format, timestruct)
        return datetime        

class XmlMessageFormatter(_AlarmFormatter):
    """
        Fixed xml formatter that features a very simple, non-configurable
        xml schema that includes pertinent information about the alarm.
    """
    def format(self, stateevent):
        actionevent = stateevent.action
        alarmevent = stateevent.get_alarm_event()
        alarm = alarmevent.source
        entry = {}
        entry['alarm'] = alarm.name
        entry['description'] = alarm.description
        entry['origin'] = alarmevent.origin
        entry['GUID'] = alarmevent.GUID
        entry['stateGUID'] = stateevent.GUID
        entry['actionGUID'] = actionevent.GUID
        entry['timestamp'] = actionevent.timestamp
        entry['datetime'] = self.datetime(actionevent.timestamp)
        entry['state'] = stateevent.name
        if alarm.priority:
            entry['priority'] = alarm.priority
        else:
            entry['priority'] = 'Normal'
        entry['actuator'] = actionevent.actuatorstr
        entry['context'] = actionevent.context
        entry['action'] = stateevent.tostring()
        message = '<?xml version="1.0" encoding="utf-8"?>\n'
        formatter = SGMLFormatter()
        formatter.open_tag('event')
        for name, value in entry.items():
            formatter.open_tag(name)
            formatter.add_text(str(value))
            formatter.close_tag(name, True)
        formatter.close_tag('event')
        return message + formatter.output_complete()
    
class AlarmMessageFormatter(_AlarmFormatter):
    """
        Fixed email format that produces an email message 
        providing what is considered to be pertinent information 
        about the alarm.
    """
    def format(self, stateevent):
        entry = {}
        actionevent = stateevent.action
        alarmevent = stateevent.get_alarm_event()
        alarm = alarmevent.source
        entry['alarm'] = alarm.name
        entry['description'] = alarm.description
        entry['origin'] = alarmevent.origin
        entry['GUID'] = alarmevent.GUID
        entry['stateGUID'] = stateevent.GUID
        entry['actionGUID'] = actionevent.GUID
        entry['timestamp'] = actionevent.timestamp
        self._timestamp = actionevent.timestamp
        entry['state'] = stateevent.name
        entry['priority'] = alarm.priority
        if not alarm.priority:
            entry['priority'] = 'Normal'
        entry['actuator'] = actionevent.actuatorstr
        entry['context'] = actionevent.context
        entry['action'] = stateevent.tostring()
        if entry.has_key('subject'):
            subject = entry['subject']
        else:
            subject = '%s (%s): %s' % (
                entry['alarm'], entry['origin'], entry['state'])
        date = self.datetime(entry["timestamp"])
        header = 'Subject: %s\r\n' % subject
        header += 'Date: %s\r\n\r\n' % date
        message = '%s %s\n' % (entry['state'], date)
        if entry['description']:
            message += 'Alarm description: %s\n' % (entry['description'],)
        message += 'Actuator: %s.\n' % (entry['actuator'],)
        message += 'Context: %s.\n\n' % (entry['context'],)
        message += entry['action']
        return header + message

# Backwards compatible change.
AlarmFormatter = AlarmMessageFormatter

class AlarmFieldFormatter(_AlarmFormatter):
    """
        More configurable alarm email formatter.
        
        Parses alarm name and description to select named fields  
        to include in message body.  Fields are on separate lines 
        of output message body.  Field names in the source alarm 
        are separated by colons.
        
        Email subject line uses a fixed format: 
            [<priority>] Alarm <alarm-name>: <status>
        
        Alarm name may be used to specify 'Asset' and 'Point'.
        
        Alarm description may contain an arbitrary set of 
        name/value pairs.  Each pair is defined on a separate 
        line, with a colon ":" separated the name from value.
        
        Certain fields are prioritized, and will automatically 
        be placed in a line higher than those of lower priority 
        and those without priority.  Those without priority are 
        sorted alphabetically and inserted after the last of 
        the prioritized fields.  
        
        The prioritized fields (high-low) are: 
            Site, Location, Timestamp, Priority, Asset, 
            Point, Value, and State.
        
        Then the set of unknown fields are listed alphabetically.
        
        The the last field is always: Description.
        
        A few fields have values pulled from the alarm events 
        themselves.  These fields are name, priority, state, 
        and value.  The value field is populated from the alarm 
        context, using either a value labeled "input", or one 
        labeled "parameter 1".
    """
    FIELDS = ("Site", "Location", "Timestamp", 
              "Priority", "Asset", "Point", "State","Context")
    ###
    # NOTE: Temporary usage of 'entry' to store information
    #  from events in dictionary object is kept so that a
    #  decision to support other formatters will require few changes;
    #  namely this portion of the processing would move up to exporter.
    ###
    def format(self, stateevent):
        event = stateevent.get_alarm_event()
        alarm = event.source
        audit = event.history + [event.current_event]
        trigger = audit[0]
        timestamp = stateevent.action.timestamp
        timevalue = time.asctime(time.localtime(timestamp))
        priority = alarm.priority
        data = {}
        head,sep,tail = alarm.name.partition(":")
        if tail:
            asset = head
            point = tail
            head,sep,tail = point.rpartition(": ")
            if head:
                point = head
                value = tail
            else:
                value = ""
        else:
            point = head
            value = ""
            asset = ""
        data["Asset"] = asset
        data["Point"] = point
        data["State"] = stateevent.name
        data["Value"] = value
        data["Priority"] = alarm.priority
        data["Timestamp"] = time.asctime(time.localtime(timestamp))
        umsg=stateevent.action.user_msg
        if(umsg != None):
            umsg=str(umsg)
            umsg1=umsg.replace('\n',' ')
            umsg2=umsg1.replace('\\n',' ')
            data["Context"] = umsg2
        else:
            data["Context"]=umsg

        if(type(stateevent.action.context) is types.DictType):
            if stateevent.action.context.has_key("input"):
                data["Value"] = str(stateevent.action.context["input"])
            elif stateevent.action.context.has_key("parameter 1"):
                #data["Value"] = str(stateevent.action.context["parameter 1"])
                msg = str(stateevent.action.context["parameter 1"])
                sorted_params=stateevent.action.context.keys()
                sorted_params.sort()
                cntr=1
                msg=msg+'\n'
                for p in sorted_params:
                        if(cntr != 1):
                            msg=msg+'Value%s: %s\n' %(str(cntr-1),stateevent.action.context[p])
                        cntr=cntr+1
                value_msg = msg
                data["Value"] = value_msg

        for line in StringIO(alarm.description).readlines():
            name,sep,value = line.partition(":")
            if name and sep and value:
                name = name.strip().capitalize()
                value = value.strip()
                if name == "Input":
                    try:
                        node = as_node(value)
                    except:
                        msglog.log("broadway", msglog.types.WARN, 
                                   "Unable to get input node: %r" % value)
                        msglog.exception(prefix="handled")
                else:
                    data[name] = value.lstrip()
            else:
                msglog.log("broadway", msglog.types.WARN, 
                           "Unable to determine key/value pair: %r" % line)
        if "Subject" in data:
            subject = data.pop("Subject")
        else:
            status = data["State"]
            priority = data["Priority"]
            subject = '[%s] Alarm %s: %s' % (priority, alarm.name, status)
        date = self.datetime(timestamp)
        header = 'Subject: %s\r\n' % subject
        header += 'Date: %s\r\n\r\n' % date
        message = []
        message.append("Subject: %s" % subject)
        message.append("Date: %s" % date)
        # Terminate header section.
        message.append("")
        description = ""
        fields = list(filter(data.has_key, self.FIELDS))
        names = set(data) - set(fields)
        names.discard("Description")
        fields.extend(sorted(names))
        if "Description" in data:
            fields.append("Description")
        items = [(field, data[field]) for field in fields]
        message.extend(["%s: %s" % item for item in items])
        return "\r\n".join(message)

class AlarmDictionaryFormatter(_AlarmFormatter):
    def format(self, stateevent):
        entry = {}
        actionevent = stateevent.action
        alarmevent = stateevent.get_alarm_event()
        alarm = alarmevent.source
        entry['name'] = alarm.name
        entry['guid'] = alarmevent.GUID
        entry['origin'] = alarmevent.origin
        entry['stateGUID'] = stateevent.GUID
        entry['actionGUID'] = actionevent.GUID
        entry['timestamp'] = actionevent.timestamp
        entry['state'] = stateevent.name
        entry['priority'] = alarm.priority
        if not alarm.priority:
            entry['priority'] = 'Normal'
        entry['actuator'] = actionevent.actuatorstr
        entry['context'] = actionevent.context
        entry['description'] = stateevent.tostring()
        fields = ['name', 'guid', 'origin',
                  'stateGUID', 'actionGUID',
                  'timestamp', 'state', 'priority',
                  'actuator', 'context', 'description']
        return map(entry.get, fields)

class LoggingTransporter(CompositeNode):
    implements(ITransporter)
    def configure(self, config):
        self.setattr('log', config.get('log', '/services/logger/Alarm Log'))
        self.setattr('transport_type', 'log-file')
        return super(LoggingTransporter, self).configure(config)
    def configuration(self):
        config = super(LoggingTransporter, self).configuration()
        config['log'] = str(self.getattr('log'))
        config['transport_type'] = self.getattr('transport_type')
        return config
    def start(self):
        self._log = self.nodespace.as_node(self.log)
        return super(LoggingTransporter, self).start()
    def transport(self, values):
        self._log.add_entry(values)
    def is_setup(self):
        return hasattr(self, '_log')

class AlarmExporter(CompositeNode):
    implements(IAlarmExporter)
    FORMATS = {"message": AlarmMessageFormatter, 
               "named-values": AlarmFieldFormatter,
               "xml-simple-schema": XmlMessageFormatter}
    TRANSPORTS = {"smtp": SMTPTransporter, 
                  "log-file": LoggingTransporter,
                  "ftp": FTPTransporter,
                  "sftp": SFTPTransporter,
                  "http-post": HTTPPostTransporter}
    def __init__(self, *args):
        self._timestamp = 0
        self.use_pool = True
        self.format = "message"
        self.transport = "smtp"
        self.formatter = None
        self.connection = None
        self.transporter = None
        self.time_function = time.localtime
        self.sources = weakref.WeakKeyDictionary()
        self.format_config = {"name": "Alarm Formatter", "parent": self}
        self.transport_config = {"name": "Alarm Transporter", "parent": self}
        super(AlarmExporter, self).__init__(*args)
    def configure(self,config):
        super(AlarmExporter, self).configure(config)
        if not self.formatter:
            self.format = config.get("format", self.format).lower()
        if not self.transporter:
            self.transport = config.get("transport", self.transport).lower()
        if "formatter" in config:            
            self.format_config.update(config["formatter"])
            if self.formatter:
                self.configure_formatter(self.format_config)
        if "transporter" in config:            
            self.transport_config.update(config["transporter"])
            if self.transporter:
                self.configure_transporter(self.transport_config)
        if "connection" in config:
            self.connection = as_node(config["connection"])
        self.setattr('timeout', int(config.get('timeout', 30)))
        self.setattr('retries', int(config.get('retries', 1)))
        self.setattr('gm_time', as_boolean(config.get('gm_time', 1)))
        self.setattr('description', config.get('description', ''))
    def configuration(self):
        config = super(AlarmExporter, self).configuration()
        config['timeout'] = str(self.getattr('timeout'))
        config['retries'] = str(self.getattr('retries'))
        config['gm_time'] = str(self.getattr('gm_time'))
        config['description'] = str(self.getattr('description'))
        if self.connection:
            config['connection'] = as_node_url(self.connection)
        config["format"] = self.format
        if self.formatter:
            config['formatter'] = self.formatter.configuration()
        else:
            config["formatter"] = self.format_config.copy()
        config["transport"] = self.transport
        if self.transporter:
            config['transporter'] = self.transporter.configuration()
        else:
            config["transporter"] = self.transport_config.copy()
        return config
    def start(self):
        if self.gm_time:
            self.time_function = time.gmtime
        else:
            self.time_function = time.localtime
        if not self.connection:
            self.connection = as_node("/services/network")
        if not self.formatter:
            self.setup_formatter()
        if not self.transporter:
            self.setup_transporter()
        return super(AlarmExporter, self).start()
    def add_child(self, child):
        result = super(AlarmExporter, self).add_child(child)
        if IAlarmFormatter.providedBy(child) or hasattr(child, 'format'):
            self.formatter = child
        elif ITransporter.providedBy(child) or hasattr(child, 'transport'):
            self.transporter = child
        return result
    def _add_child(self, child): 
        pass
    def scheduled_time(self):
        return self._timestamp
    def add_source(self, source, *eventtypes):
        if not eventtypes:
            eventtypes = [StateEvent]
        elif len(eventtypes) == 1 and isinstance(eventtypes[0], (tuple,list)):
            eventtypes = eventtypes[0]
        source = self.nodespace.as_node(source)
        self.remove_source(source)
        eventtypes = map(eventlookup.get, eventtypes)
        slow = isinstance(self.get_transporter(), 
            (SMTPTransporter, FTPTransporter, HTTPPostTransporter, SFTPTransporter))
        subid = source.dispatcher.register_for_types(
            self.export, eventtypes, None, not slow)
        self.sources[source] = (subid, eventtypes)
        return subid
    def remove_source(self, source):
        source = self.nodespace.as_node(source)
        if not self.sources.has_key(source): 
            return
        source.dispatcher.unregister(self.sources[source][0])
        del(self.sources[source])
        return source
    def get_sources(self):
        return self.sources.keys()
    def get_source_names(self):
        return [source.name for source in self.get_sources()]
    def get_source_urls(self):
        return [source.url for source in self.get_sources()]
    def get_events(self, source):
        return self.sources[source][1]
    def get_event_names(self, source):
        eventtypes = self.get_events(source)
        return filter(None, map(eventnamelookup.get, eventtypes))
    def get_source_dictionary(self, names = True):
        """
            Returns dictionary mapping source names to
            event type names.  Supplying false for optional
            'names' parameter will cause value to be event
            objects rather than names.
        """
        dictionary = {}
        for source in self.get_event_sources():
            if names: values = self.get_event_names(source)
            else: values = self.get_events(source)
            dictionary[source.name] = values
        return dictionary
    def trigger_configuration(self):
        """
            Get mapping of trigger source node URLs to trigger event names.
        """
        sources = self.get_sources()
        sourceurls = [source.url for source in sources]
        eventnames = [self.get_event_names(source) for source in sources]
        triggers = dict(zip(sourceurls, eventnames))
        return triggers
    def configure_triggers(self, configuration):
        # Include all existing sources so ones not being 
        # configured are removed.  Configuration is all inclusive.
        sources = set(self.get_source_urls())
        sources.update(configuration)
        for source in sources:
            events = configuration.get(source, [])
            if events:
                self.add_source(source, *events)
            else:
                self.remove_source(source)
        return self.trigger_configuration()
    def setup_formatter(self):
        if not self.formatter:
            datatype = self.FORMATS[self.format]
            self.formatter = self.nodespace.create_node(datatype)
        self.configure_formatter(self.format_config)
    def setup_transporter(self):
        if not self.transporter:
            datatype = self.TRANSPORTS[self.transport]
            self.transporter = self.nodespace.create_node(datatype)
        self.configure_transporter(self.transport_config)
    def get_formatter(self):
        return self.formatter
    def get_transporter(self):
        return self.transporter
    def configure_formatter(self, config):
        return self.get_formatter().configure(config)
    def configure_transporter(self, config):
        return self.get_transporter().configure(config)
    def export(self, stateevent):
        attempts = 0
        transported = False
        formatter = self.get_formatter()
        transporter = self.get_transporter()
        if not (formatter.is_setup() and transporter.is_setup()):
            print 'Exporter not fully configured for transport.'
            return
        data = self.get_formatter().format(stateevent)
        while not transported and (attempts <= self.retries):
            try:
                if self.connection.acquire(self.timeout):
                    try: 
                        self.get_transporter().transport(data)
                    finally: 
                        self.connection.release()
                    transported = True
            except: 
                msglog.exception(prefix="handled")
            attempts += 1
        if not transported: 
            raise MpxException('Export %s failed.' % data)
        return transported

