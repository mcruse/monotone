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
# Refactor 2/11/2007
import time
import urllib
import urllib2
from mpx.lib import msglog
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node
from mpx.lib.configure import as_boolean
from mpx.lib.exceptions import Unauthorized
from mpx.service.network.http.response import Response
from mpx.www.w3c.syndication.rss1.interfaces import IRSS1Document
from mpx.www.w3c.syndication.rss2.interfaces import IRSS2Document
from mpx.www.w3c.syndication.atom.interfaces import IAtomDocument
from mpx.service.alarms2.alarmevent import AlarmEvent
from mpx.componentry import ComponentLookupError
from mpx.componentry import query_multi_adapter
from mpx.componentry.security.interfaces import ISecure


class SyndicationViewer(CompositeNode):
    interfaces = {'rss': IRSS2Document,
                  'rss1': IRSS1Document,
                  'rss2': IRSS2Document,
                  'atom': IAtomDocument}
    def __init__(self, *args, **kw):
        self.default = "rss2"
        self.secured = True
        self.user_service = None
        self.user_manager = None
        self.path = "/syndication"
        self.provides_security = True
        self.subject = "/services/Alarm Manager"
        self.cloud_manager = "/services/Cloud Manager"
        super(SyndicationViewer, self).__init__(*args, **kw)
    def configure(self, config):
        if "path" in config:
            self.path = config["path"]
        if "secured" in config:
            self.secured = as_boolean(config["secured"])
        if "provides_security" in config:
            self.provides_security = as_boolean(config["provides_security"])
        if "cloud_manager" in config:
            self.cloud_manager = config["cloud_manager"]
        if "subject" in config:
            self.subject = config["subject"]
        if "default" in config:
            self.default = config["default"]
        return super(SyndicationViewer, self).configure(config)
    def configuration(self):
        config = super(SyndicationViewer, self).configuration()
        config['path'] = self.path
        config['default'] = self.default
        config['subject'] = self.subject
        config['secured'] = str(self.secured)
        config["cloud_manager"] = self.cloud_manager
        config["provides_security"] = str(self.provides_security)
        return config
    def start(self):
        self._subject = as_node(self.subject)
        if self.secured:
            self.security_manager = as_node('/services/Security Manager')
            self.user_service = self.security_manager.user_manager
        else:
            self.user_service = None
            self.security_manager = None
        self.user_manager = as_node("/services/User Manager")
        self._cloud_manager = as_node(self.cloud_manager)
        super(SyndicationViewer, self).start()
    def stop(self):
        super(SyndicationViewer, self).stop()
        self._subject = None
        self._cloud_manager = None
        self.security_manager = None
        self.user_manager = None
        self.user_service = None
    def match(self, path):
        return path.startswith(self.path)
    def handle_request(self, request):
        exceptions = []
        userobject = request.user_object()
        if not userobject:
            username = request.get_cookie("NBMUSER", None)
            if not username:
                raise Unauthorized("User unknown")
            address = request.get_address()
            if not self._cloud_manager.is_host_in_formation(address):
                raise Unauthorized("Address unrecognized: " + address)
            message = "Getting user because address/usrename: %r, %r"
            msglog.debug(message % (address, username))
            userobject = self.user_manager.get_user(username)
        request_data = request.get_post_data_as_dictionary()
        request_data.update(request.get_query_string_as_dictionary())
        if request_data.has_key('command') and request_data.has_key('guid'):
            exceptions = []
            path = request.get_path()
            username = userobject.name()
            method = request.get_command()
            protocol = request.get_protocol()
            command = request_data['command'][0]
            user = self.user_service.user_from_object(userobject)
            origins = {}
            for guid in request_data['guid']:
                try:
                    event = AlarmEvent.get_event(guid)
                except KeyError:
                    msglog.warn("Attempt to get event %r failed." % guid)
                else:
                    origins.setdefault(event.origin, []).append(event)
            for origin,events in origins.items():
                if origin == AlarmEvent.LOCALORIGIN:
                    for event in events:
                        message = "User '%s'" % username
                        if self.secured:
                            event = query_multi_adapter((event,user), ISecure)
                        try:
                            event.notify(command, self, time.time(), message)
                        except Exception,error:
                            msg = "Notify %r of %r failed." % (event, command)
                            msglog.log("broadway", msglog.types.WARN, msg)
                            msglog.exception(prefix="handled")
                            # CSCte94039 - form the proper error msg
                            exceptions.append((command, str(error)))
                else:
                    headers = {"Cookie": "NBMUSER=%s" % userobject.name()}
                    guids = [event.GUID for event in events]
                    parameters = [("command", command)]
                    parameters.extend([("guid", guid) for guid in guids])
                    data = urllib.urlencode(parameters)
                    url = '%s://%s%s' % (protocol, origin, path)
                    if method == "GET":
                        url = "?".join([url, data])
                        data = None
                    redirect = urllib2.Request(url, data, headers)
                    try:
                        urllib2.urlopen(redirect).read()
                    except Exception,error:
                        message = "'%s' remote events on '%s' failed."
                        msglog.warn(message % (command, origin))
                        msglog.exception(prefix="handled")
                        exceptions.append((origin, command, error))
        if exceptions:
            messages = ["Some actions failed:"]
            for errdata in exceptions:
                messages.append("  " + str(errdata))
            request['Content-Type'] = 'text/plain'
            request.error(405, "\n".join(messages))
            return
        data = ""
        response = Response(request)
        style = request_data.get('type', self.default)
        if isinstance(style, (list, tuple)):
            style = style[0]
        if style != "none":
            interface = self.interfaces.get(style)
            if interface is None:
                request['Content-Type'] = 'text/plain'
                request.error(405, 'Invalid or unsupported feed type.')
                return
            try:
                syndicator = interface(self._subject)
            except ComponentLookupError, error:
                request['Content-Type'] = 'text/plain'
                request.error(404, 'No adapter for requested node.')
                return
            clientid = request_data.get('clientid')
            if clientid is not None:
                clientid = clientid[0]
            data = syndicator.render(request.get_path(), clientid)
            response.set_header('Content-Type', 'text/xml')
        response.send(data)
