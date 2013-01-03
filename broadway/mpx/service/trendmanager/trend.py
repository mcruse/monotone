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
import copy
import urllib

import mpx.lib
from mpx.lib import msglog

from mpx.componentry import implements

from mpx.lib.configure import set_attribute, get_attribute, REQUIRED, as_boolean

from mpx.lib.exceptions import ENameInUse
from mpx.lib.exceptions import ENoSuchName

from mpx.lib.node import Alias
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_internal_node
from mpx.lib.node import as_deferred_node
from mpx.lib.node import as_node_url
from mpx.lib.node import as_node

from interfaces import ITrend
from interfaces import ITrendPointConfiguration
from interfaces import ITrendPreferenceConfiguration

##
# This class basically exists to use the adapter model consistantly in the
# request_handler.  Feels like overkill...
class TrendPointConfiguration(object):
    implements(ITrendPointConfiguration)
    def __init__(self, trend):
        self.trend = trend
        return

class TrendPreferenceConfiguration(object):
    implements(ITrendPreferenceConfiguration)
    def __init__(self, trend):
        self.trend = trend
        return

class TrendBase(CompositeNode):
    DEFAULT_PREFERENCES = {
        "width":800,
        "height":600,
        "title":None,
        "text":{"fontname":"Verdana",
                "fontsize":12,
                "color":0xD0D5D8,},
        "background":{"color":0x1F282D,},
        "timespan":{"value":10, "unit":"samples"},
        "time-reference":"mediator", # mediator, UTC, or browser
        "y-axes":[
            {"enable":True,
             "from":"auto",
             "to":"auto",
             "type":"numeric",
             "map":{},
             },
            {"enable":False,
             "from":"auto",
             "to":"auto",
             "type":"binary",
             "map":{},
             },
            ],
        "points":[{"color":0xFF0000, "y-axis":1,},
                  {"color":0x00FF00, "y-axis":1,},
                  {"color":0x0000FF, "y-axis":1,},
                  {"color":0xFFFF00, "y-axis":1,},
                  {"color":0x00CC00, "y-axis":1,},
                  {"color":0x0000CC, "y-axis":1,},
                  {"color":0xCCCC00, "y-axis":1,},
                  {"color":0x00CCCC, "y-axis":1,},
                  {"color":0xCC00CC, "y-axis":1,},
                  ],
        }
    def __init__(self, *args):
        super(TrendBase, self).__init__(*args)
        self.periodic_log=None
        self.log_url=None
        return
    def configure(self, config):
        set_attribute(self, 'preferences', {}, config, self.merge_preferences)
        super(TrendBase, self).configure(config)
        return
    def configuration(self):
        config = super(TrendBase, self).configuration()
        get_attribute(self, 'preferences', config, self.merge_preferences)
        return config
    def merge_container(self, destination, source):
        if isinstance(destination, dict):
            for key,value in source.items():
                if destination.has_key(key):
                    target = destination[key]
                    if isinstance(target, (dict,list,tuple)):
                        if isinstance(target, tuple):
                            target = list(target)
                            destination[key] = target
                        self.merge_container(target, value)
                    elif target is None:
                        destination[key] = copy.deepcopy(source[key])
                else:
                    destination[key] = copy.deepcopy(source[key])
        elif isinstance(destination, list):
            for i in xrange(0, len(source)):
                value = source[i]
                if i == len(destination):
                    destination.append(copy.deepcopy(value))
                else:
                    target = destination[i]
                    if isinstance(target, (dict,list,tuple)):
                        if isinstance(target, tuple):
                            target = list(target)
                            destination[i] = target
                        self.merge_container(target, value)
                    elif target is None:
                        destination[i] = copy.deepcopy(source[key])
        return
    def merge_preferences(self, preferences):
        try:
            default_preferences = copy.deepcopy(TrendBase.DEFAULT_PREFERENCES)
            if self.log_url:
                default_preferences["title"] = as_internal_node(
                    self.log_url
                    ).name
            self.merge_container(preferences, default_preferences)
        except:
            msglog.exception()
            raise
        return preferences
    def get_preferences(self):
        return self.configuration()['preferences']
    def get_points(self):
        return self.configuration()['points']
    def get_period(self):
        return self.periodic_log.period
    def convert_time_reference(self, reference):
        # Some day maybe we'll nationalize this...
        return {
            "Mediator":"mediator",
            "UTC":"UTC",
            "Browser":"browser",
            }.get(reference,"mediator")
    def convert_timespan(self, value, unit):
        timespan_map = {
            "samples":self.get_period(),
            "seconds":1,
            "minutes":60,
            "hours":3600,
            "days":86400,
            "weeks":604800,
            "months":2419200, # 28 days.  Could be smarter.
            "years":31536000, # 365 days.           
        }
        return float(value) * timespan_map.get(unit, self.get_period())
    def delete_existing_data(self):
        self.periodic_log.trim_ge('timestamp',0)
        return

class Trend(TrendBase):
    implements(ITrend)
    def __init__(self, *args):
        super(Trend, self).__init__(*args)
        self.__running = False
        self.klass='trend'
        return
    def configure(self, config):
        name = config.get('name', self.name)
        parent = as_node_url(config.get('parent', self.parent))
        if parent and name:
            self.create_logger_alias(parent, name)
        set_attribute(self, 'period', REQUIRED, config, int)
        set_attribute(self, 'points', REQUIRED, config, tuple)
        set_attribute(self, 'externally_managed', False, config, as_boolean)
        super(Trend, self).configure(config)
        return
    def configuration(self):
        config = super(Trend, self).configuration()
        get_attribute(self, 'period', config)
        get_attribute(self, 'points', config)
        get_attribute(self, 'externally_managed', config)
        return config
    def start(self):
        if self.__running:
            return
        if self.has_child(self.name):
            self.periodic_log = self.get_child(self.name)
        else:
            self.periodic_log = mpx.lib.factory(
                'mpx.service.logger.periodic_log.factory'
                )
        self.periodic_log.configure({
            'parent':self,
            'name':self.name,
            'period':self.period,
            'debug':self.debug,
            })
        self.log_url = self.periodic_log.as_node_url()
        if self.periodic_log.has_child('columns'):
            self.periodic_log.get_child('columns').prune()
        columns = mpx.lib.factory('mpx.service.logger.column.Columns')
        columns.configure({
            'parent':self.periodic_log,
            'name':'columns',
            })
        column = mpx.lib.factory('mpx.service.logger.periodic_column.factory')
        column.configure({
            'parent':columns,
            'name':'timestamp',
            'debug':self.debug,
            'sort_order':'ascending',
            'position':0,
            'context':'None',
            'args':'()',
            'function':'self.scheduled_time',
            'conversion':'magnitude',
            })
        position = 0
        for point in self.points:
            position += 1
            point_name = point['name']
            point_node = point['node']
            column = mpx.lib.factory(
                'mpx.service.logger.periodic_column.factory'
                )
            column.configure({
                'parent':columns,
                'name':point_name,
                'debug':self.debug,
                'sort_order':'none',
                'position':position,
                'context':'None',
                'args':'()',
                'function':'mpx.lib.node.as_node(%r).get' % (
                point_node
                ),
                'conversion':'magnitude',
                })
        super(Trend, self).start()
        self.__running = True
        return
    def stop(self):
        super(Trend, self).stop()
        self.__running = False
        return
    def destroy(self):
        if self.__running:
            self.stop()
        if self.periodic_log is not None:
            if self.periodic_log.log is not None:
                self.periodic_log.log.destroy()
        self.destroy_logger_alias()
        return
    ##
    # Create an alias for this node's periodic_log child in /services/logger.
    # This serves several purposes:
    # 1. Avoids log file name conflicts.  I think other mechanisms also prevent
    #    that (the Trend Manager "autodiscovers" logs).
    # 2. Allows interacting with Trends as regular logs, specifically done for
    #    the log_download_service.
    def create_logger_alias(self, parent, name):
        logger_service = as_internal_node('/services/logger')
        if logger_service.has_child(name):
            # get_child returns the actual child, as_node would follow an
            # alias.
            trend_alias = logger_service.get_child(name)
            name_in_use = not isinstance(trend_alias, Alias)
            if not name_in_use:
                name_in_use |= as_internal_node(
                    os.path.dirname(trend_alias.node_url)
                    ) is not self
            if name_in_use:
                raise ENameInUse(trend_alias.as_node_url())
        else:
            trend_alias = Alias()
            parent_url = as_node(parent).as_node_url()
            quoted_name = urllib.quote(name,'')
            trend_alias.configure(
                {'name':name, 'parent':logger_service,
                 'node_url':os.path.join(parent_url, quoted_name, quoted_name)}
                )
        return
    def destroy_logger_alias(self):
        logger_service = as_internal_node('/services/logger')
        if logger_service.has_child(self.name):
            trend_alias = logger_service.get_child(self.name)
            # get_child returns the actual child, as_node would follow an
            # alias.
            if isinstance(trend_alias, Alias):
                try:
                    if as_internal_node(
                        os.path.dirname(trend_alias.node_url)
                        ) is self:
                        trend_alias.prune()
                except ENoSuchName:
                    trend_alias.prune()
        return

class PeriodicLogTrendAdapter(TrendBase):
    implements(ITrend)
    def __init__(self, *args):
        super(PeriodicLogTrendAdapter, self).__init__(*args)
        self.klass='log'
        self.__running = False
        return
    def configure(self, config):
        super(PeriodicLogTrendAdapter, self).configure(config)
        return
    def configuration(self):
        config = super(PeriodicLogTrendAdapter, self).configuration()
        return config
    def start(self):
        if self.__running:
            return
        super(PeriodicLogTrendAdapter, self).start()
        self.periodic_log = as_internal_node(
            '/services/logger'
            ).get_child(self.name)
        self.log_url = self.periodic_log.as_node_url()
        self.__running = True
        return
    def stop(self):
        super(PeriodicLogTrendAdapter, self).stop()
        self.__running = False
        return
    def get_points(self):
        points = []
        columns = []
        for column in self.periodic_log.get_child('columns').children_nodes():
            if hasattr(column, 'position') and int(column.position) != 0:
                columns.append(column)
        columns.sort(lambda a, b: cmp(int(a.position), int(b.position)))
        for column in columns:
            # Scary voodoo to determine the Node asscoiated with the get.
            import mpx.lib.node
            func = column.configuration()['function']
            function = eval(func)
            try:
                node_url = function.im_self.as_node_url()
            except AttributeError:
                # could be RNA - try to parse from configuration info. and check
                # if it's really a node
                node_url = func[func.find('(')+2:func.rfind(')')-1]
                node_url = as_node(node_url).as_node_url()
            points.append({'name':column.name, 'node':node_url})
        return points
    def destroy(self):
        # @fixme Raise a better exception...
        raise 'Trend Manager will not delete logs.'
