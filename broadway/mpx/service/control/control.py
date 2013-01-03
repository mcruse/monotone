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
import os, time, cPickle
import mpx.service.control
from mpx.lib.exceptions import EInvalidValue
from mpx.lib import msglog
from mpx.lib import thread_pool
from mpx.lib.configure import parse_xml
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.node import as_node
from mpx.lib.node import CompositeNode
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.scheduler import scheduler
from mpx.service.control.load_xml import load_root as load_tim_root
from mpx.ion.rz.load_xml import load_root as load_rz_root
        
from mpx import properties

# change to True to allow runtime reloading of applications.
ALLOW_APP_RELOAD = False

## set up path to where configuration files are located
config_path = os.path.join(properties.CONFIGURATION_DIR,
              'services/control/')
try:
    os.makedirs(config_path)
except:
    pass #must have already existed


class Control(CompositeNode):
    ##
    # This attribute is used in the introspective generation
    # of configuration data.
    __module__ = mpx.service.control.__name__
    
    def __init__(self):
        CompositeNode.__init__(self)
        self._status = 'initialized'
        self._stale_apps = []
    def configure(self, config):
        self._pdo = PersistentDataObject(self)
        self._pdo.stats_dict = {} #used to detect changes to xml files based on timestamp. Tuple (modify time, pickle string)
        self._pdo.load()
        # write_priority can be set for the entire control service, though
        # it may be specialized at the individual application node level. 
        set_attribute(self, 'write_priority', 9, config, int)
        CompositeNode.configure(self, config)
    def configuration(self):
        config = CompositeNode.configuration(self)
        self.pdo_file = self._pdo.filename()
        get_attribute(self, 'write_priority', config)
        get_attribute(self, 'pdo_file', config, str)
        return config
    def _save_pdo(self): #no locking needed since the load and save cannot overlap
        start_time = time.time()
        self._pdo.save()
        msglog.log(self.as_node_url(),msglog.types.INFO,
                   'Control service configuration data saved in: %s seconds' % (str(time.time() - start_time),))
    def start(self):
        self._status = 'starting'
        self.stats_dict = {} #clear out stats dict to force reload of app
        self.application_change_detector(1) #starting
    def _start(self):
        CompositeNode.start(self) #get the children ready for a trip...
        #now that the children are started, go back through the list and finish up the "graphical compile"
        for n in self.children_nodes():
            if n.hasattr('map_output_connections'):
                n.map_output_connections()
        for n in self.children_nodes():
            if n.hasattr('map_reference_output_connections'):
                n.map_reference_output_connections()
        for n in self.children_nodes():
            if n.hasattr('resolve_inputs'):
                n.resolve_inputs()
        for n in self.children_nodes():
            if n.hasattr('prepare_run_list'):
                n.prepare_run_list()
        for n in self.children_nodes():
            if n.hasattr('trigger_run_list'):
                n.trigger_run_list()
    def prune_orphaned_schedules(self):
        # remove schedules under /services/time/local/TIM that have no app
        manager = as_node('/services/time/local')
        if manager.has_child('TIM'):
            try:
                sh = as_node('/services/time/local/TIM')
                name_header = 'RZSched_'
                # create list of RZSched_'s under the TIM node
                schedules = filter(lambda k:k[:len(name_header)] == name_header, sh.children_names())
                # compare appname after RZSched_, upto : with our children names
                orphans = filter(lambda k:k.split('_')[1].split(':')[0] not in self.children_names(), schedules)
                for o in orphans:
                    try:
                        sh.get_child(o).prune()
                        msglog.log('Graphical Control:', 'pruned orphaned schedule: ', o)
                    except:
                        msglog.exception()
                if len(orphans):
                    sh.save_schedule()
            except:
                msglog.exception()

    def check_and_load_application_files(self, starting=0):
        app_reloaded = starting #return value to signal that the children need to be started
        save_pdo = 0 #flag to control saving config data to pdo
        files = os.listdir(config_path) #/var/mpx/config/services/control (usually)
        xml_filenames = []
        for f in files:
            if f.find('.xml') > 0 and len(f) == (f.find('.xml') + 4): #any xml file in this folder is assumed to be a control app
                xml_filenames.append(f)
                modify_time = os.stat(config_path + f)[8]
                stale_pdo = True
                no_stats_pdo = True
                if f in self._pdo.stats_dict: #check for change since last time
                    no_stats_pdo = False
                    if self._pdo.stats_dict[f][0] == modify_time:
                        stale_pdo = False #old news, no change detected
                #self.stats_dict[f]=modify_time
                if starting or no_stats_pdo or (stale_pdo and ALLOW_APP_RELOAD): #need to (re)load application
                    if app_reloaded == 0: #only stop all application nodes for the first detected change
                        try:
                            self._status = 'Stopping %s' % (f,)
                            msglog.log(self.as_node_url(),msglog.types.INFO,
                                'Stage 0:  Stop Application templates.')
                            for c in self.children_nodes():
                                if hasattr(c, '_stop_running_app'):
                                    c._stop_running_app()
                        except:
                            msglog.exception()
                    app_reloaded = 1 #no need to "stop" for any other app changes
                    self._status = 'Loading %s' % (f,)
                    try:
                        root = None
                        if not stale_pdo: #so no change was detected, we are starting up the framework
                            try: #to get the pickled config data rather than load the xml again
                                msglog.log(self.as_node_url(),msglog.types.INFO,
                                       'Stage 1:  XML unchanged.  Loading configuration data from PDO: %s' % (f,))
                                root = cPickle.loads(self._pdo.stats_dict[f][1])
                            except:
                                msglog.exception()
                                msglog.log(self.as_node_url(),msglog.types.WARN,
                                       'Stage 1:  Unable to reload config data. Next, try XML file.')
                        if root is None:
                            msglog.log(self.as_node_url(),msglog.types.INFO,
                                       'Stage 1:  Parsing configuration xml file: %s' % (f,))
                            root = parse_xml(config_path + f)
                            self._pdo.stats_dict[f] = (modify_time, cPickle.dumps(root))
                            save_pdo = 1
                            if f in self._stale_apps:
                                self._stale_apps.remove(f)
                        #now we have the root configuration.  Turn it into configured nodes
                        module = root.get_config().get('module', None)
                        if module == 'mpx.ion.rz.rzhost_node.RzhostNode':
                            load_rz_root(root, self)
                        elif module == 'mpx.service.control.graphical.ApplicationNode':
                            load_tim_root(root, self)
                        else:
                            raise EInvalidValue()
                    except Exception, e:
                        msglog.exception()
                        pass
                elif stale_pdo:
                    if not f in self._stale_apps:
                        msglog.log(self.as_node_url(), msglog.types.INFO,
                                   'Application %s has been modified, please restart the framework.' % (f,))
                        self._stale_apps.append(f)
                        try:
                            self.get_child(f.split('.')[0]).set_stale_flag()
                        except:
                            msglog.exception()
                            
        #clear out any leftover pdo for  deleted files
        for k in self._pdo.stats_dict.keys():
            try:
                if k not in xml_filenames:
                    save_pdo = 1 #force save of modififed pdo
                    del self._pdo.stats_dict[k]
                    n = k.split('.xml')[0]
                    if self.has_child(n): # prune any running app who's file was deleted
                        try:
                            self.get_child(n).prune()
                            self.prune_orphaned_schedules()
                        except:
                            msglog.exception()
            except:
                pass
        if save_pdo:
            thread_pool.LOW.queue_noresult(self._save_pdo)
        return app_reloaded
    def application_change_detector(self, starting=0):
        try:
            if self.check_and_load_application_files(starting):
                self._status = 'Starting control applications'
                msglog.log(self.as_node_url(),msglog.types.INFO,
                   'Stage 5:  Start Application templates.')
                self._start()
                self._status = 'Running'
                msglog.log(self.as_node_url(),msglog.types.INFO,
                   'Application templates started.')
                self.prune_orphaned_schedules()
                # schedule manager must see control service as running to work
            scheduler.after(13, self.application_change_detector)
        except:
            self._status = 'ERROR: check message log'
            msglog.exception()
            scheduler.after(60, self.application_change_detector)
    def find_template_named(self, name):
        #name should be in the form ../jobname/definitionname.  return the node
        if name.find('../') != 0: return None
        try:
            print name
            n = name.replace('%2F','/')
            x, a, t = n.split('/',2)
            print x,a,t
            if self.has_child(a):
                print 'found: ',a
                n = self.get_child(a)
                print 'node: ', n.as_node_url()
                answer = n.find_template_named(t)
                if answer:
                    print 'template: ', answer.as_node_url()
                else:
                    print 'template not found: ', str(t)
                return answer
            #tie in rznet peer apps here!!
            #look in the com ports for a matching rz net peer app
            # interfaces = as_node('/interfaces')
            # for n in interfaces.children_nodes():
                # if n.has_child('rznet_peer'):
                    # rznp = n.get_child('rznet_peer')
                    # if rznp.has_child(a): #found the app
                        ##form url for template
                        # answer = rznp.as_node('%s/%s' %(a,t))
                        # print 'found rznp template: ', answer.as_node_url()
                        # return answer
        except:
            msglog.exception()
        return None
    def get(self, skipcache=0):
        return self._status