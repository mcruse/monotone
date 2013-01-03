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
from mpx.componentry import Interface

class ITrendManager(Interface):
    def get_trend(self, trend_name):
        """
        Return an instance that implements ITrend interface of an existing
        trend (or trendable log).
        """
    def get_trends(self, trend_name):
        """
        Return a list of all existing trend (or trendable log) instances that
        implement ITrend interface.
        """
    def new_trend(self):
        """
        Return an instance that implements ITrend interface for new trend.
        """
    def get_points(self):
        """
        Return an object representing the points in the graph.
        """
    def get_preferences(self):
        """
        Return an object representing the preferences for the graph.
        """

class ITrend(Interface):
    """
    An interface that allows us to think of Trends as a single entity.  Mostly
    exists at this point as a hook for the presentation layer.
    """

class ITrendPointConfiguration(Interface):
    """
    An interface to the configuration data of a Trend relating to the set
    of points to graph.  Mostly exists at this point as a hook for the
    presentation layer to hide the fact that the GraphTool is currently
    log centric.
    """

class ITrendPreferenceConfiguration(Interface):
    """
    An interface to the configuration data of a Trend relating to the display
    of the data.
    """

class IConfirmUpdateTrend(Interface):
    """
    An interface to the class responsible from validating and confirming
    trend updates.
    """
