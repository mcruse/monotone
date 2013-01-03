"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
from HTMLgen import HTMLgen

from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter

from mpx.www.w3c.xhtml.interfaces import IWebContent

from interfaces import ITrend

class HTMLTrend(object):
    implements(IWebContent)
    adapts(ITrend)
    def __init__(self, trend):
        ##
        # Trend we are adapting.
        self.trend = trend
        ##
        # The DIV where swfobject loads the Flash movie.
        self.trend_div = None
        ##
        # The script element that uses SWFObject to load trend_div
        self.graph_element = None
        return
    def render(self):
        document = HTMLgen.SimpleDocument(
            title=self.trend.name,
            stylesheet='/omega/trendmanager/styles.css',
            script=[
            HTMLgen.Script(src="/graphtool/swfobject.js"),
            ]
            )
        # Hack-around to set the class on the BODY for HTMLGen
        document.append(
            HTMLgen.Script(code="""
              document.body.className = 'trend';
              """),
            )
        self.trend_div = HTMLgen.Div(id="trend_div")
        document.append(self.trend_div)
        self.create_embedded_graph()
        document.append(self.graph_element)
        return str(document)
    def add_variable(self, name, value):
        self.graph_element.append("""so.addVariable("%s", "%s");
        """ % (name, value))
        return
    def write_preferences(self, preferences):
        def convert_color(arg):
            value = str(arg).strip()
            if value and value[0] == "#":
                value = "0x%s" % value[1:]
            try: value = "0x%06X" % int(float(value))
            except: pass
            return value
        # Set the graph's title:
        self.add_variable("CFG.titlebar.title_text", preferences['title'])
        # Set the graph's background:
        self.add_variable("CFG.background.fill_style.rgb",
                          convert_color(preferences['background']['color']))
        # Set the text preferences:
        self.add_variable("CFG.text_format.color",
                          convert_color(preferences['text']['color']))
        self.add_variable("CFG.text_format.size",
                          preferences['text']['fontsize'])
        self.add_variable("CFG.text_format.font",
                          preferences['text']['fontname'])
        # Configure the default timespan:
        self.add_variable("CFG.axes.time.default_timespan",
                          self.trend.convert_timespan(
                              preferences['timespan']['value'],
                              preferences['timespan']['unit']))
        # Configure the time-reference:  mediator, UTC, or browser
        self.add_variable("CFG.preferences.time_reference",
                          self.trend.convert_time_reference(
                              preferences['time-reference']))
        # Configure the y-axes:
        yaxes = preferences["y-axes"]
        for i in xrange(0,len(yaxes)):
            axis_id = str(i + 1)
            yaxis = yaxes[i]
            key_map = {
                "enable":yaxis['enable'],
                "range_origin":yaxis['from'],
                "range_limit":yaxis['to'],
                "type":yaxis['type'],
                }
            for key, value in key_map.items():
                graph_variable = "CFG.axes.value%s.%s" % (axis_id, key)
                self.add_variable(graph_variable, str(value).strip())
        # Set point colors and collect list of points for axis 2:
        axis1_points = []
        axis2_points = []
        axis_map = (axis1_points, axis2_points)
        points = preferences['points']
        for i in xrange(0,len(points)):
            point = points[i]
            point_id = str(i + 1)
            graph_variable = "CFG.graph.id%s.line_style.rgb" % (point_id)
            self.add_variable(graph_variable, convert_color(point['color']))
            point_axis = int(point['y-axis'])-1
            axis_points = axis_map[point_axis]
            axis_points.append(point_id)
        # Specify axis 2 points:
        self.add_variable("CFG.axes.value2.points", ','.join(axis2_points))
        return
    def create_embedded_graph(self):
        self.graph_element = HTMLgen.Script();
        preferences = self.trend.get_preferences()
        window_width = 800
        window_height = 600
        try: window_width = int(float(preferences['width']))
        except: pass
        try: window_height = int(float(preferences['height']))
        except: pass
        self.graph_element.append("""
        var so = new SWFObject("/graphtool/EmbeddedGraph.swf", "trend_swf",
                               %(width)s, %(height)s, 8);
        so.addParam("wmode", "opaque");
        """ % {"width":window_width, "height":window_height})
        self.add_variable("CFG.log_uri", self.trend.log_url)
        self.write_preferences(preferences)
        self.graph_element.append("""so.write("trend_div");
        """)
        return
register_adapter(HTMLTrend)
