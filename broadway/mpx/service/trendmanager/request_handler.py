"""
Copyright (C) 2007 2008 2010 2011 Cisco Systems

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
import time

from mpx.lib import msglog
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_deferred_node
from mpx.lib.node import as_node_url
from mpx.lib.node import as_internal_node
from mpx.service.network.http.response import Response
from mpx.www.w3c.xhtml.interfaces import IWebContent

from trendmanager import TrendManager

from mpx.lib.exceptions import ENameInUse

from trend import TrendPointConfiguration
from trend import TrendPreferenceConfiguration
from mpx.lib.exceptions import Unauthorized
from mpx.lib.node import is_node_url

class ENotAValidUrl(Exception):
    def __init__(self, node_url):
        Exception.__init__(self,"%s Not a valid trend point" %node_url)
        self.node_url = node_url
        return

class TrendManagerHandler(CompositeNode):
    REDIRECT = ('<html>\n<head>\n' +
                '<META HTTP-EQUIV="Window-target" CONTENT="_top">\n' +
                '<META http-equiv="Refresh" content="0; Url=%s" >\n' +
                '<title>%s</title>\n</head>\n<body></body>\n</html>')
    def __init__(self, *args):
        super(TrendManagerHandler, self).__init__(*args)
        self.manager = None
        self.path = None
        self.security_manager = None
        self.secured = True
        return
    def configure(self, config):
        self.setattr('path', config.get('path','/trendmanager'))
        self.setattr('name', config.get('name','Trend Manager Handler'))
        self.setattr(
            'manager',
            as_deferred_node(config.get('manager','/services/Trend Manager'))
            )
        self.secured = as_internal_node("/services").secured
        super(TrendManagerHandler, self).configure(config)
        return
    def configuration(self):
        config = super(TrendManagerHandler, self).configuration()
        config['path'] = self.getattr('path')
        config['manager'] = as_node_url(self.getattr('manager'))
        return config
    def start(self):
        if self.secured:
            self.security_manager = self.as_node("/services/Security Manager")
        super(TrendManagerHandler, self).start()
        return
    def stop(self):
        super(TrendManagerHandler, self).stop()
        return
    def match(self, path):
        return path.startswith(self.path)
    def redirect(self,request):
        url = 'trends.html?preventCache=%f' % time.time()
        request.push(TrendManagerHandler.REDIRECT % (url,self.name))
        request.done()
    def handle_request(self, request):        
        response = Response(request)
        manager = self.manager
        if self.secured:
            manager = self.security_manager.as_secured_node(manager)
        username = request.user_object().name()
        request_data = request.get_post_data_as_dictionary()
        request_data.update(request.get_query_string_as_dictionary())
        if request_data.has_key('reload'):
            self.redirect(request) 
            return
        elif request_data.has_key('viewtrend'):
            name = request_data['viewtrend'][0]
            adapt = manager.get_trend(name)
        elif request_data.has_key('newtrend'):
            try:
		name = request_data['trendname'][0].strip()
                adapt = manager.new_trend(name)
                adapt = manager
                self.redirect(request)
            except ENameInUse:
                request.error(400, "<b>%s</b> exists, Please use a different name" %
                              request_data['trendname'][0])
            except Unauthorized, e:
                request.error(403, "Permission Denied: %s"%e)
            return
        elif request_data.has_key('configurepoints'):
            try:
                name = urllib.unquote_plus(request_data['configurepoints'][0])
                adapt = TrendPointConfiguration(manager.get_trend(name))
            except Unauthorized, e:
                request.error(403, "Permission Denied: %s"%e)
           
        elif request_data.has_key('trendpreferences'):
            try:
                name = urllib.unquote_plus(request_data['trendpreferences'][0])
                adapt = TrendPreferenceConfiguration(
                    manager.get_trend(name)
                    )
            except Unauthorized, e:
                request.error(403, "Permission Denied: %s"%e)
                return
        elif request_data.has_key('-'):
            name = urllib.unquote_plus(request_data['-'][0])
            try:
                manager.delete_trend(name)
                adapt = manager
            except Unauthorized, e:
                request.error(403, "Permission Denied: %s"%e)
            except:
                # @note Do something here instead of (just) raise.
                raise
        elif request_data.has_key('trend'):
            # Configurarion pages:
            if request_data.has_key('cancelpoints'):
                # Configure Points: Cancel
                adapt = manager
                #self.redirect(request)
                #return
            elif request_data.has_key('reloadpoints'):
                # Configure Points: Reload
                name = urllib.unquote_plus(request_data['trend'][0])
                adapt = TrendPointConfiguration(manager.get_trend(name))
                
            elif request_data.has_key('commitpoints'):
                # Configure Points: Commit
                try:
                    adapt = self.commit_points(request_data)
                except Unauthorized, e:
                    request.error(403, "Permission Denied: %s"%e)
                    return
                except ENotAValidUrl,e:
                  request.error(400,str(e))
                  return  
                #self.redirect(request)
                #return
            elif request_data.has_key('cancelpreferences'):
                # Configure Preferences: Cancel
                adapt = manager
                #self.redirect(request)
                #return
            elif request_data.has_key('reloadpreferences'):
                # Configure Preferences: Reload
                name = urllib.unquote_plus(request_data['trend'][0])
                adapt = TrendPreferenceConfiguration(
                    manager.get_trend(name)
                    )
            elif request_data.has_key('commitpreferences'):
                # Configure Preferences: Commit
                try:
                    adapt = self.commit_preferences(request_data)
                except Unauthorized, e:
                    request.error(403, "Permission Denied: %s"%e)
                    return
            elif request_data.has_key('cancelupdate'):
                # Confirm Update: Cancel
                adapt = manager
                #self.redirect(request)
                #return
            elif request_data.has_key('confirmupdate'):
                # Confirm Update: Commit
                try:
                    adapt = self.confirm_update(request_data)
                except Unauthorized, e:
                    request.error(403, "Permission Denied: %s"%e)
                    return
        else:
            adapt = manager

        webadapter = IWebContent(adapt)
        response.send(webadapter.render())
        return
    def extract_trend_name(self, request_data):
        encoded_trend_name = request_data['trend'][0].strip()
        trend_name = urllib.unquote_plus(encoded_trend_name)
        return trend_name
    def extract_point_configuration(self, request_data):
        configuration = {}
        points = []
        manager = self.manager
        if self.secured:
            manager = self.security_manager.as_secured_node(manager)
        trend_name = self.extract_trend_name(request_data)
        trend = manager.get_trend(trend_name)
        for point_position in xrange(1,10):
            point_key = 'point%d' % point_position
            node_key = 'node%d' % point_position
            point_name = request_data[point_key][0].strip()
            node_name = request_data[node_key][0].strip()
            if point_key and node_name:
                points.append({'name':point_name, 'node':node_name})
        configuration['points'] = points
        configuration['period'] = request_data['period'][0].strip()
        return configuration
    def confirm_update(self, request_data):
        assert request_data.has_key('confirmupdate')
        manager = self.manager
        if self.secured:
            manager = self.security_manager.as_secured_node(manager)
        configuration = self.extract_point_configuration(request_data)
        trend_name = self.extract_trend_name(request_data)
        deletedata = int(request_data['deletedata'][0])
        confirmation = manager.update_trend(trend_name, configuration,
                                                 confirmed=1,
                                                 deletedata=deletedata)
        assert confirmation == None
        return manager
    def commit_points(self, request_data):
        assert request_data.has_key('commitpoints')
        manager = self.manager
        if self.secured:
            manager = self.security_manager.as_secured_node(manager)
        configuration = self.extract_point_configuration(request_data)
        for point_map in configuration['points']:
            if not is_node_url(point_map['node']):
                raise ENotAValidUrl(point_map['node'])
        trend_name = self.extract_trend_name(request_data)
        confirmation = manager.update_trend(trend_name, configuration)
        if confirmation != None:
            return confirmation
        return manager
    def commit_preferences(self, request_data):
        manager = self.manager
        if self.secured:
            manager = self.security_manager.as_secured_node(manager)
        assert request_data.has_key('commitpreferences')
        encoded_trend_name = request_data['trend'][0]
        trend_name = urllib.unquote_plus(encoded_trend_name)
        trend = manager.get_trend(trend_name)
        preferences = {}
        preferences['title'] = request_data['displayname'][0]
        preferences['width'] = request_data['width'][0]
        preferences['height'] = request_data['height'][0]
        preferences['background'] = {}
        preferences['background']['color'] = request_data['backgroundcolor'][0]
        preferences['text'] = {}
        preferences['text']['color'] = request_data['textcolor'][0]
        preferences['text']['fontsize'] = request_data['textsize'][0]
        preferences['text']['fontname'] = request_data['textfont'][0]
        preferences['timespan'] = {}
        preferences['timespan']['value'] = request_data['timespanvalue'][0]
        preferences['timespan']['unit'] = request_data['timespanunit'][0]
        preferences['time-reference'] = request_data['timereference'][0]
        axes = []
        def get_value(request_data, field, section, position):
            key = "%s%s%s" % (field, section, position)
            if request_data.has_key(key):
                return request_data[key][0]
            return None
        for axis_id in ("1","2"):
            axes.append({"to":
                         get_value(request_data, "to", "axis", axis_id),
                         "from":
                         get_value(request_data, "from", "axis", axis_id),
                         "enable":
                         get_value(request_data, "enable", "axis", axis_id),
                         "type":
                         get_value(request_data, "type", "axis", axis_id),
                         })
        preferences['y-axes'] = axes
        points = []
        for i in xrange(0,10):
            position = i + 1
            point_color = get_value(request_data, "color", "point", position)
            point_axis = get_value(request_data, "axis", "point", position)
            if None in (point_color, point_axis):
                break
            points.append({"color":point_color,
                           "y-axis":point_axis})
        preferences['points'] = points
        configuration = {"preferences":preferences}
        confirmation = manager.update_trend(trend_name, configuration)
        if confirmation != None:
            return confirmation
        return manager
