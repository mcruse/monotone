"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
from mpx.lib.configure import REQUIRED,set_attribute,get_attribute
from mpx.service.network.http.request_handler import RequestHandler
from mpx.service.network.http.response import Response
from mpx.lib.node import as_node_url, as_node
from mpx.lib.exceptions import ENoSuchName
from mpx.lib import msglog
import cgi

class AlarmBrowser(RequestHandler):
    def configure(self, config):
        RequestHandler.configure(self, config)
        set_attribute(self,'request_path','alarms',config)
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'request_path', config)
    def start(self):
        self._alarm_managers = as_node('/services/alarms').children_nodes()
    def match(self, path):
        if path.startswith(self.request_path):
            return 1
        return 0
    def handle_request(self,request):
        response = Response()
        if request.has_query():
            params = request.get_query_dictionary()
            if not params.has_key('action') or params['action'] != 'ack':
                return response.send('<H1>Unknown Query</H1>')
            alarm_url = request.get_path()[len(self.request_path):]
            try:
                alarm = as_node(alarm_url)
            except ENoSuchName:
                return response.send('<H1>Unknown Alarm</H1>')
            alarm.acknowledge()
            return response.send('<H1>The alarm has been notified</H1>')
        response.send(self._build_manager_page())
    def _build_manager_page(self):
        html_lines = ['<html><body>']
        for manager in self._alarm_managers:
            html_lines.append('<h2>%s</h2>' % manager.name)
            for alarm in manager.get_child('alarms').children_nodes():
                pass
