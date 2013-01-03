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

from mpx.componentry import implements

from interfaces import IConfirmUpdateTrend

class ConfirmUpdateTrend(object):
    implements(IConfirmUpdateTrend)
    def __init__(self, trend, new_cfg):
        import copy
        self.encoded_name = urllib.quote_plus(trend.name)
        self.trend = trend
        self.old_cfg = trend.configuration()
        # Assumes that configuration is only Python objects, which should
        # be true.
        self.new_cfg = copy.deepcopy(new_cfg)
        self.old_name = self.old_cfg.get('name')
        self.new_name = self.new_cfg.get('new_name', self.old_name)
        self.old_period = str(self.old_cfg.get('period')).strip()
        self.new_period = str(self.new_cfg.get('period',
                                               self.old_period)).strip()
        self.old_points = self.old_cfg.get('points')
        self.new_points = self.new_cfg.get('points', self.old_points)
        self.old_preferences = self.old_cfg.get('preferences')
        self.new_preferences = self.new_cfg.get('preferences',
                                                self.old_preferences)
        self.change_name = self.new_name != self.old_name
        self.change_period = self.new_period != self.old_period
        self.change_points = self.new_points != self.old_points
        self.change_preferences = self.new_preferences != self.old_preferences
        # Will GT be confused by the change to the data.
        # @fixme In a perfect world, GT could survive SOME of this better.
        # self.delete_level == 0:  GT will not be confused.
        # self.delete_level == 1:  GT may be confused.
        # self.delete_level == 2:  GT will be confused.
        self.delete_level = 0
        return
    def __str__(self):
        attr_strs = []
        for name in self.__dict__:
            attr_strs.append('%s: %r' % (name, self.__dict__[name]))
        return '\n'.join(attr_strs)
    def requires_confirmation(self):
        if self.change_points:
            self.delete_level = 0
            if len(self.old_points) == 0:
                return False
            if len(self.old_points) > len(self.new_points):
                return False
            if len(self.new_points) > len(self.old_points):
                # GT WILL be confused by old _seq.
                self.delete_level = 2
                return True
            # GT may be confused.
            self.delete_level = 1
            for i in xrange(0,len(self.old_points)):
                old_point = self.old_points[i]
                new_point = self.new_points[i]
                if old_point['node'] != new_point['node']:
                    return True
                if old_point['name'] != new_point['name']:
                    return True
            self.delete_level = 0
        return False
    def requires_stop_and_restart(self):
        return True in (self.change_name, self.change_period,
                        self.change_points)
    def configuration_changed(self):
        return True in (self.change_name, self.change_period,
                        self.change_preferences, self.change_points)
    def configuration(self):
        return self.new_cfg
    def original_configuration(self):
        return self.old_cfg
