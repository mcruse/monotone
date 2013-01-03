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
import os
import md5
import cPickle
import urllib
from threading import Lock

from mpx.componentry import implements
from mpx.componentry.interfaces import IPickles

from mpx.lib import msglog
from mpx.lib import node

from mpx.lib.exceptions import ENameInUse
from mpx.lib.exceptions import ENotRunning
from mpx.lib.exceptions import ENoSuchName

from mpx.lib.persistent import PersistentDataObject
from mpx.lib.persistence.datatypes import PersistentDictionary

from mpx.service.garbage_collector import GC_NEVER


from trend import Trend
from trend import PeriodicLogTrendAdapter
from trend import TrendPointConfiguration
from trend import TrendPreferenceConfiguration

from interfaces import ITrend
from interfaces import ITrendManager
from interfaces import ITrendPointConfiguration
from interfaces import ITrendPreferenceConfiguration

from confirm import ConfirmUpdateTrend

from mpx.lib.neode.node import IConfigurableNode
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node_url
from mpx.lib.node import as_internal_node
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation

# If the log has more than MAX_TRENDABLE_COLUMNS (9), then the EmbeddedGraph
# can not display it.
MAX_TRENDABLE_COLUMNS = 9

def filename(namespec, hashit=True):
    if not isinstance(namespec, basestring):
        namespec = as_node_url(namespec)
    if hashit:
        namespec = md5.new(namespec).hexdigest()
    return namespec

def marshal(trend):
    # IConfigurableNode is so IPickles finds the right adapter...
    trend = IConfigurableNode(trend)
    return cPickle.dumps(IPickles(trend))

def unmarshal(trenddump):
    return IPickles(cPickle.loads(trenddump))()

class TrendManager(CompositeNode):
    implements(ITrendManager)
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self, *args):
        super(TrendManager, self).__init__(*args)
        self.logger_url = None
        self.trends = None
        self._pdo_lock = Lock()
        self._trendconfig = None
        self.__running = False
        self.secured = True
        return
    def _persist_trend_configuration(self, trend):
        self._pdo_lock.acquire()
        try:
            self._trendconfig[trend.name] = marshal(trend)
        finally:
            self._pdo_lock.release()
        return
    def _delete_trend_configuration(self, trend_name):
        self._pdo_lock.acquire()
        try:
            if self._trendconfig.has_key(trend_name):
                del self._trendconfig[trend_name]
        finally:
            self._pdo_lock.release()
        return
    def configure(self, config):
        self.setattr('name', config.get('name','Trend Manager'))
        self.setattr('logger_url', config.get('logger_url','/services/logger'))
        self.secured = as_internal_node("/services").secured
        super(TrendManager, self).configure(config)
        return
    def configuration(self):
        config = super(TrendManager, self).configuration()
        config['logger_url'] = self.getattr('logger_url')
        return config
    def start(self):
        try:
            self._pdo_lock.acquire()
            try:
                if self.__running:
                    return
                self.__running = True
                self._trendconfig = PersistentDictionary(
                    filename(self), encode=None, decode=None)
                if not self._trendconfig:
                    pdodata = PersistentDataObject(self, dmtype=GC_NEVER)
                    if os.path.exists(pdodata.filename()):
                        msglog.log('broadway', msglog.types.INFO, 
                                   "Migrating previous trend data")
                        pdodata.trends = {}
                        pdodata.load()
                        self._trendconfig.update(pdodata.trends)
                    del(pdodata)
            finally:
                self._pdo_lock.release()
            super(TrendManager, self).start()
            self.logger = node.as_internal_node(self.logger_url)
            if self.has_child('trends'):
                self.trends = self.get_child('trends')
            else:
                self.trends = CompositeNode()
                self.trends.configure({'parent':self, 'name':'trends'})
                self.trends.start()
            corrupt_trends = []
            for trendname,trenddump in self._trendconfig.items():
                msg = "Loading trend: %s" % trendname
                msglog.log('trendmanager', msglog.types.INFO, msg)
                try:
                    trend = unmarshal(trenddump)
                except:
                    corrupt_trends.append(trendname)
                    msg = "Failed to load trend: %s" % trendname
                    msglog.log('trendmanager', msglog.types.ERR, msg)
                    msglog.exception(prefix = 'Handled')
            for trendname in corrupt_trends:
                try:
                    msg = "Deleting trend information: %s" % trendname
                    msglog.log('trendmanager', msglog.types.INFO, msg)
                    self._delete_trend_configuration(trendname)
                    if self.trends.has_child(trendname):
                        trend = self.trends.get_child(trendname)
                        trend.prune(force=True)
                except:
                    msglog.exception(prefix = 'Handled')
        except:
            self.__running = False
            raise
        return
    def stop(self):
        self.__running = False
        super(TrendManager, self).stop()
        return
    def is_trendable(self, log_node):
        if log_node.configuration().has_key('period'):
            # Assume a log with a period is valid.
            return True
        if not log_node.has_child('columns'):
            # If the log does not have a columns container, than it doesn't
            # look like a proper log.
            return False
        column_nodes = log_node.get_child('columns').children_nodes()
        if not column_nodes:
            # If the log does not have any columns, than it doesn't
            # look like a proper log.
            return False
        if len(column_nodes) > MAX_TRENDABLE_COLUMNS:
            # If the log has more than MAX_TRENDABLE_COLUMNS (9), then the
            # EmbeddedGraph can not display it.
            return False
        has_timestamp = False
        for column in column_nodes:
            column_configuration = column.configuration()
            if not column_configuration.has_key('name'):
                # OK, this should NEVER happen...
                return False
            if column_configuration['name'] == 'timestamp':
                has_timestamp = True
            if not column_configuration.has_key('conversion'):
                # To be safe, each column must have a conversion...
                return False
            if column_configuration['conversion'] != 'magnitude':
                # And the conversion must be a 'magnitude'
                return False
        if not has_timestamp:
            # Graph requires a timestamp.
            return False
        return True
    security.protect('get_trends', 'View')
    def get_trends(self):
        if not self.__running: raise ENotRunning()
        trend_names = []
        for name in self.trends.children_names():
            trend_names.append(name)
        for log_node in self.logger.children_nodes():
            trend_name = log_node.name
            if not trend_name in trend_names:
                if (self.is_trendable(log_node)):
                    trend_adapter = PeriodicLogTrendAdapter()
                    trend_adapter.configure({
                        'parent':self.trends,
                        'name':trend_name,
                        })
                    trend_adapter.start()
                    self._persist_trend_configuration(trend_adapter)
                    trend_names.append(trend_name)
        trend_names.sort()
        trends = []
        for trend_name in trend_names:
            trends.append(self.trends.get_child(trend_name))
        return trends
    security.protect('get_trend', 'View')
    def get_trend(self, trend_name):
        if not self.__running: raise ENotRunning()
        if not self.trends.has_child(trend_name):
            # Autodiscoveresque.
            self.get_trends()

        # @fixme Raise a better exception...        
        return self.trends.get_child(trend_name)
    
    def get_trend_preferences(self, trend_name):
        trend_name = urllib.unquote_plus(trend_name)
        trend = self.get_trend(trend_name)
        preferences = trend.get_preferences()
        points = trend.get_points();
        for i in xrange(0,len(points)):
          try:
               points[i]["color"] = preferences["points"][i]["color"] = "#%06X" % int(preferences["points"][i]["color"])
          except:
               points[i]["color"] = preferences["points"][i]["color"]
          points[i]["y-axis"] = preferences["points"][i]["y-axis"]
        preferences["points"] = points
        try:
           preferences["background"]["color"]="#%06X" % int(preferences["background"]["color"])
        except:
           pass
        try:
           preferences["text"]["color"]="#%06X" % int(preferences["text"]["color"])
        except:
           pass
        msglog.log("broadway", msglog.types.INFO, "Preferences: %r"%preferences)
        return preferences

    security.protect('delete_trend', 'Configure')
    def delete_trend(self, trend_name):
        if not self.__running: raise ENotRunning()
        self._delete_trend_configuration(trend_name)
        if not self.trends.has_child(trend_name):
            # Autodiscoveresque.
            self.get_trends()
        # @fixme Raise a better exception...
        trend = self.trends.get_child(trend_name)
        trend.prune()
        trend.destroy()
        return
    security.protect('update_trend', 'Configure')
    def update_trend(self, trend_name, new_cfg, **kw):
        if not self.__running: raise ENotRunning()
        confirmed = kw.get('confirmed',0)
        deletedata = kw.get('deletedata',0)
        trend = self.get_trend(trend_name)
        confirmation = ConfirmUpdateTrend(trend, new_cfg)
        #@fixme, dleimbro
        if 0:#not confirmed and confirmation.requires_confirmation():
            return confirmation
        if confirmation.configuration_changed():
            try:
                if deletedata:
                    trend.delete_existing_data()
                if confirmation.requires_stop_and_restart():
                    trend.stop()
                trend.configure(confirmation.configuration())
                if confirmation.requires_stop_and_restart():
                    trend.start()
            except:
                msglog.exception()
                try: trend.stop()
                except: msglog.exception()
                trend.configure(confirmation.original_configuration())
                trend.start()
                raise
            else:
                self._persist_trend_configuration(trend)
        return None
    def _new_trend(self, name):
        if not self.__running: raise ENotRunning()
        """
        Return an instance that implements ITrend interface for new trend with
        no points.
        """
        new_trend = Trend()
        period = 60;
        points = []
        preferences = {}        
        new_trend.configure({'parent':self.trends,
                             'name':name,
                             'period':period,
                             'points':points,
                             'preferences':preferences})
        return new_trend
    security.protect('new_trend', 'Configure')
    def new_trend(self, name=None):
        if name:
            return self._new_trend(name)
        while True:
            try:
                new_trend = self._new_trend(self.generate_trend_name())
                break    #was going into loop and generating thousands of trends. 
                         #This breaks loop when an unused (generated) trend name is found
            except ENameInUse:
                continue
            
        return new_trend
    security.protect('generate_trend_name', 'View')
    def generate_trend_name(self):
        i_trend = 1
        while True:
            try:
                self.get_trend('Trend %d' % i_trend)
                i_trend += 1
            except ENoSuchName:
                break
        return ('Trend %d' % i_trend)
