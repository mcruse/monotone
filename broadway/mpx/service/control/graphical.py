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
import time, types, string, struct, weakref
from moab.linux.lib import uptime
from array import array
from copy import copy
from types import *
from mpx.lib.node import ConfigurableNode, CompositeNode, as_node_url, as_internal_node, as_node, is_node
#from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
#from mpx.lib.node.proxy import ProxyAbstractClass
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib import msglog
#from mpx.ion import Result
#from mpx.lib import Callback
from mpx.lib.thread_pool import ThreadPool
from mpx.lib.threading import Lock
from mpx.lib.persistent import PersistentDataObject
from mpx.service import garbage_collector
from mpx.lib.exceptions import *
from mpx.lib import EnumeratedValue
from mpx.lib.scheduler import scheduler
from mpx.lib.scheduler import Scheduler
from mpx.lib import thread_pool
from mpx.service.control.rpn_functions import Rpn, get_function
from mpx.service.garbage_collector import GC_NEVER
from mpx.lib.exceptions import Exception, EInvalidValue
import cPickle
from mpx.service.subscription_manager import SUBSCRIPTION_MANAGER as SM
from mpx.lib.event import EventConsumerMixin
from mpx.lib.entity.overridable import is_overridable
from mpx.lib.event import ChangeOfValueEvent
from mpx.lib.event import EventProducerMixin
import as_html 

#def nodecmp(a,b):
#    if a.hasattr('nodecmp'):
#        return a.nodecmp(b)
#    return cmp(a.name,b.name)

# Application holds one or more Drawings.  
#Drawings are processed in alphbetical order.
#period is execution trigger rate. is adjustable, default 1 second

class ApplicationNode(CompositeNode,EventConsumerMixin):
    scheduler = Scheduler()
    def __init__(self):
        CompositeNode.__init__(self)
        EventConsumerMixin.__init__(self, self._mpx_get_cov_event_handler, self._mpx_get_exception_handler)
        self.lock = Lock() #used to keep the trigger logic thread safe
        self._executing = 0
        self._run_list = []
        self._run_continuously = 0
        self.run_time = None #initally ALL of the time is idle
    	self.scheduled_run_time = 0
        self.scheduled_execution = None
        self.rpn = Rpn()
        self.__reference_cache = {}
        self._running = 0
        self._scheduler = None
        self.exception_list = None
        self.persistent_values = {}
        self.overrides = {} #dict of active overrides.  persistent
        self._new_override = 0 #flag to control saving of persistant data
        self._last_saved_time = 0 #time overrides were last saved
        self._pdo = None
        self._pdo_lock = Lock()
        self._save_pdo_schedule = None
        self._mpx_get_sid = None
        self._mpx_get_subscriptions = {}
        self._new_mpx_get_subscriptions = {}
        self.subscription_exceptions = None
        self.schedule_save_pdo = 0
        self.need_to_save_pdo = 0 # markeva: When not defined, _run_templates()
                                  # perpetually throws an AttributeError after
                                  # successfully running (so it wasn't obvious).
        self._schedule_names = {} # used to detect orphaned left over schedules
        self.use_cov = 0  # control use of cov by templates
        self._status = 'Initialized'
        return
    def configure(self, config):
        set_attribute(self, 'debug', 0, config, int)
        CompositeNode.configure(self, config)
        set_attribute(self, 'period', 1.0, config, float)
        if hasattr(self.parent, 'write_priority'):
            default_write_prio = self.parent.write_priority
        else:
            default_write_prio = 9
        set_attribute(self, 'write_priority', default_write_prio, config, int)
        set_attribute(self, 'override_save_delay', 61.0, config, float)
        set_attribute(self, 'override_save_delay_maximum', 307.0, config, float)
        set_attribute(self, 'use_cov', self.use_cov, config, int)
        ###
        # self.debug = 1
        ###
        #prime numbers are used for the time delays to avoid "aliasing" issues with other periodic processes
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'run_time', config, str)
        get_attribute(self, 'period', config, str)
       	get_attribute(self, 'write_priority', config, str)
        get_attribute(self, 'exception_list', config, str)
        get_attribute(self, 'subscription_exceptions', config, str)
        self.pdo_file = self.get_pdo().filename()
        get_attribute(self, 'pdo_file', config, str)
        get_attribute(self, 'use_cov', config, str)
        return config
    def start(self):
        self.rpn.startup = 1 # reset the firstrun logic to get more logging
        self._status = 'Starting'
        if not self.scheduler.is_started():
            try:
                self.scheduler.start()
            except:
                msglog.exception(prefix="handled")
        if not self._running:
            self._mpx_get_sid = SM.create_delivered(self) #ID of subscription used for all descendent mpx_get templates
            self._running = 1
            CompositeNode.start(self) #get the children ready for a trip...
        #now that the children are started, go back through the list and finish up the "graphical compile"
    def stop(self):
        self._running = 0
        if self.scheduled_execution:
            try:
                self.scheduled_execution.cancel()
            except:
                pass
        self.scheduled_execution = None
        self.scheduled_run_time = 0
        CompositeNode.stop(self)
        if self._save_pdo_schedule is not None:
            try:
                self._save_pdo_schedule.cancel()
            except:
                pass #can't stop stopping....
        self._save_pdo_schedule = None
        self._save_pdo()
        self._pdo = None
        if self._mpx_get_sid:
            try:
                SM.destroy(self._mpx_get_sid)
            except:
                pass
            self._mpx_get_sid = None
    def _stop_running_app(self):
        self._running = 0
    def map_output_connections(self):
        for n in self.children_nodes():
            if n.hasattr('map_output_connections'):
                n.map_output_connections()
    def map_reference_output_connections(self):
        for n in self.children_nodes():
            if n.hasattr('map_reference_output_connections'):
                n.map_reference_output_connections()
    def resolve_inputs(self):
        for n in self.children_nodes():
            if n.hasattr('resolve_inputs'):
                n.resolve_inputs()
    def prepare_run_list(self):
        self._run_list = []
        names = self.children_names()
        names.sort()
        for k in names: #alphabetical run order
            n = self.get_child(k)
            if n.hasattr('generate_run_list'):
                self._run_list.extend(n.generate_run_list())
        #start a periodic trigger to run the child drawings
        self._run_list = tuple(self._run_list)
        #restore saved overrides
        self.get_pdo_into_overrides()
    def trigger_run_list(self):
        if self.debug: 
            print 'Application %s started' % (self.name,)
            for n in self._run_list:
                print '  ', n.url
        self._schedule_execution()
    def _schedule_execution(self):
        if not self._running:
            return
        scheduled = self.scheduled_execution
        if scheduled:
            msglog.warn("%s rescheduling %s." % (self, scheduled))
            try:
                scheduled.cancel()
            except:
                msglog.exception(prefix="handled")
        current = uptime.secs()
        if self.scheduled_run_time:
            nextrun = self.scheduled_run_time + self.period
        else:
            nextrun = current + self.period
        self.scheduled_run_time = max(nextrun, current + 0.1)
        delay = self.scheduled_run_time - current
        if self.debug > 2:
            msglog.debug("%s next runs after %0.3f secs." % (self, delay))
        self.scheduled_execution = self.scheduler.after(delay, self._runexec)
    def _runexec(self):
        self.scheduled_execution = None
        try:
            result = self._execute()
        finally:
            self._schedule_execution()
        return result
    def _execute(self):
     	start_time = uptime.secs()
        #run through all the child drawings
        self._exception_list = []
        try:
            self._run_templates()
        except Exception,e:
            if self.debug or self.first_run():
                msglog.exception(e)
            self.last_exception = str(e)
        self.exception_list = self._exception_list
        run_time = uptime.secs() - start_time
        if self.run_time is None:
            self.run_time = run_time
            self.first_run_time = run_time
        self.run_time = ((self.run_time * 3) + run_time) / 4 #average run time
    def _run_templates(self):
        #if self.debug: print 'App run: ', self.name
        rpn = self.rpn
        rpn.init_math_stack()
        self._mpx_get_subscriptions = {}
        [t._run() for t in self._run_list]
        if self.first_run():
            self._prune_orphaned_schedules()
            self.rpn.startup = 0 #rpn startup only true for first run
        if len(self._mpx_get_subscriptions) and self._mpx_get_sid: #add any new subscriptions to the master subscription
            SM.merge(self._mpx_get_sid, self._mpx_get_subscriptions)
        if self.need_to_save_pdo:
            self.need_to_save_pdo = 0
            self._schedule_save_pdo()
    def first_run(self): # log exceptions more during first run
        return self.rpn.startup
    def _prune_orphaned_schedules(self):
        manager = as_node('/services/time/local')
        if manager.has_child('TIM'):
            try:
                sh = as_node('/services/time/local/TIM')
                name_header = 'RZSched_' + self.name
                # collect names of schedules for this app under shedule hander TIM node
                app_schedules = filter(lambda k:k.split(':')[0] == name_header, sh.children_names())
                # create list of schedules with this app name that are no longer used 
                # print 'schedule names: ', self._schedule_names, 'app schedules: ', app_schedules
                orphans = filter(lambda k:k not in self._schedule_names, app_schedules)
                for o in orphans:
                    try:
                        sh.get_child(o).prune()
                        msglog.log('Graphical Control', self.as_node_url(), 'pruned orphaned schedule: %s' % (o))
                    except:
                        msglog.exception()
                if len(orphans):
                    sh.save_schedule()
            except:
                msglog.exception()
    def get_template_definition_node(self, name):
        return self.as_node('template_library/' + name)
    def find_template_named(self, name):
        #name is in the form 'drawing_name/template_name' or '../app_name/drawing_name/template_name'
        if name in self.__reference_cache:
            return self.__reference_cache[name]
        try:
            node = self.as_node(name) #this will find nodes in the app or sister apps but not rznp apps
            self.__reference_cache[name] = node
            return node
        except:
            if name.find('../') == 0:
                answer = self.parent.find_template_named(name) #this is why they all restart at once when there is a change
                if answer:
                    #self.__reference_cache[name] = answer  ##don't cache nodeds external to this app
                    return answer
        return None
    def reference_cache(self):
        return self.__reference_cache
    def _save_pdo(self):
        self._pdo_lock.acquire()
        try:
            self._last_saved_time = uptime.secs()
            overrides = copy(self.overrides) #these might change on another thread
            overrides = dict([(k,v.outputs) for (k,v) in overrides.items()])
            self.get_pdo().overrides = cPickle.dumps(overrides)
            persistent_values = copy(self.persistent_values) 
            pvs = dict([(k,v.outputs) for (k,v) in persistent_values.items()])
            self._pdo.persistent_values = cPickle.dumps(pvs)
            self._pdo.use_cov = self.use_cov
            self._pdo.save()
            if self.debug: print 'saved pdo: %s value: %s' % (self.as_node_url(),self._pdo.overrides,)
        finally:
            self._pdo_lock.release()
    def _queue_save_pdo(self): #only call while protected by Lock
        self._save_pdo_schedule = None
        thread_pool.LOW.queue_noresult(self._save_pdo)
    def _schedule_save_pdo(self): #call while locked
        #delay saving by one minute.  If other overrides occur within that minute, wait no longer than 5 minutes to save overrides
        if self._save_pdo_schedule is not None:
            if self._last_saved_time + self.override_save_delay_maximum > uptime.secs():
                #since max delay has not occured, delay again to collect as may overrides into one write as possible
                try:
                    self._save_pdo_schedule.cancel()
                except:
                    pass
                self._save_pdo_schedule = None
        if self._save_pdo_schedule is None:
            self._save_pdo_schedule = scheduler.after(self.override_save_delay, self._queue_save_pdo)
    def get_pdo(self): #call while locked
        if self._pdo is None:
            self._pdo = PersistentDataObject(self, dmtype=garbage_collector.GC_NEVER)
            self._pdo.overrides = '(d.' #pickled empty dict
            self._pdo.persistent_values = '(d.' #pickled empty dict
            self._pdo.use_cov = self.use_cov # default
            self._pdo.load()
        return self._pdo
    def get_pdo_into_overrides(self):
        self._pdo_lock.acquire()
        try:
            self.get_pdo()
            if self.debug: print 'load pdo: %s value: %s' % (self.as_node_url(),self._pdo.overrides,)
            pvs = cPickle.loads(self._pdo.persistent_values) #dict of node url and output registers
            self.persistent_values.clear()
            for k,v in pvs.items():
                try:
                    c = as_node(k)
                    self.persistent_values[k] = c
                    c.outputs = array('f',v)#[:]
                    c._outputs = copy(c.outputs) #v[:]
                except:
                    if self.debug: print 'node %s in persistent value list is missing' % (k,)
            overrides = cPickle.loads(self._pdo.overrides) #dict of node url and output registers
            self.overrides.clear()
            for k,v in overrides.items():
                try:
                    c = as_node(k)
                    self.overrides[k] = c
                    c.outputs = array('f',v) #[:]
                    c._outputs = copy(c.outputs) #v[:]
                    c._override = 1
                except:
                    if self.debug: print 'node %s in override list is missing' % (k,)
            self.use_cov = self._pdo.use_cov
        finally:
            self._pdo_lock.release()
    def new_override(self, template):
        #when a template is overridden (set), put it in the list to be saved
        #self._pdo_lock.acquire()
        #try:
        if template._override:
            self.overrides[template.url] = template #replaced by current outputs when stored
        else:
            try:
                del self.overrides[template.url]
            except:
                pass #it may not exist 
        self.need_to_save_pdo = 1
            #self._schedule_save_pdo() #in one minute save the override to disk. 
        #finally:
            #self._pdo_lock.release()
    def new_persistent_value(self, template):
        #when a template is overridden (set), put it in the list to be saved
        #self._pdo_lock.acquire()
        #try:
        if template.persistent:
            self.persistent_values[template.url] = template #replaced by current outputs when stored
        else:
            del self.persistent_values[template.url]
        self.need_to_save_pdo = 1
        #self._schedule_save_pdo() #in one minute save the override to disk. 
        #finally:
            #self._pdo_lock.release()
    def _mpx_get_cov_event_handler(self, cve):
        if self.debug:
            print self.as_node_url(), ' : ', str(cve)
        answer = cve.results()
        if isinstance(answer, dict):
            [as_node(k)._mpx_get_cov_event_handler(v) for (k,v) in answer.items()]
    def _mpx_get_exception_handler(self, e):
        self.subscription_exceptions = str(e)
    def subscribe(self, template, node):
        self._mpx_get_subscriptions[template.url] = node
    def unsubscribe(self, template):
        #remove the mpx_get point from the subscriptions
        SM.remove(self._mpx_get_sid, template.url)
    def template_run_times(self):
        sum = 0
        for t in self._run_list:
            if t.last_run_time:
                sum += t.last_run_time
        return sum
        #return [(t.as_node_url(), t.last_run_time) for t in self._run_list]
    def _has_cov(self):
        # this controls child templates use of cov
        # but this node itself has no subscribable value
        return self.use_cov
    def set_cov_mode(self, cov=None): # used from command line to control cov
        if cov is None: # toggle
            cov = not self.use_cov
        self.use_cov = cov
        self.need_to_save_pdo = 1
    def set_stale_flag(self):
        self._status = 'Source xml file has changed, restart required.'
# a Drawing consists of Templates/Macros/Constants/Texts & Connections
# loosely ported from phwin smalltalk object    
class DrawingNode(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self._run_list = [] #list of Templates and Macros in execution order
        self.references = None #list of Reference to template/macro/node on different page
        self.constants = None #list of Constants
        self.texts = None #list of Text objects
        self.connections = None #list of the Connections in the drawing
        self.description = None #string
        self.font = Font()
    def configure(self, config):
        CompositeNode.configure(self, config)
        self.debug = self.parent.debug
        set_attribute(self, 'connections', [], config)
        self._init_connections()
        set_attribute(self, 'references', [], config)
        set_attribute(self, 'constants', [], config)
        self._init_constants()
        set_attribute(self, 'texts', [], config)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'debug', config, int)
        get_attribute(self, 'connections', config)
        get_attribute(self, 'references', config)
        get_attribute(self, 'constants', config)
        get_attribute(self, 'texts', config)
        get_attribute(self, '_connections', config, str)
        get_attribute(self, '_constants', config, str)
        return config
    def start(self):
        self.rpn = self.parent.rpn
        CompositeNode.start(self)
        
        #compile the drawing
        #follow connections and link the template inputs to other nodes
    def nodebrowser_handler(self, nb, path, node, node_url):
        #create html for link to monitor drawing
        block = ['<div class="node-section node-drawing-link">']
        block.append('<h2 class="section-name">Monitor Drawing</h2>')
        block.append('<ul class="drawing">')
        s = self.parent.name + '/' + self.name + '.htm'
        block.append('<a href="/%s">/%s</a><br>' %(s,s))
        block.append("</ul>")
        block.append("</div>")
        drawing_link = "\n".join(block)
        # get default dict from node browser and add link
        dct = nb.get_default_presentation(node, node_url)
        dct['drawing-link'] = drawing_link
        # answer the html for the modified node browser page
        return '''    %(node-hierarchy)s
     %(node-name)s
     %(drawing-link)s
     %(node-children)s
     %(node-configuration)s
     %(node-persistence)s''' % dct
    def map_output_connections(self): #2nd phase of startup
        #generate a Dict for x,y vs nodes for THIS drawing
        self._output_connections = {} #key: (x,y), value: node
        #for each template or macro in this drawing, generate a map of output connection points
        for n in self.children_nodes():
            if n.hasattr('map_output_connections'): #only for the templates/macros, skip other nodes
                self._output_connections.update(n.map_output_connections()) #recursive for macros
        return self._output_connections
    def map_reference_output_connections(self): #3rd phase of startup
        for r in self.references: #track down the reference and add it's outputs to the outputs_connections map
            name = r['name']
            template_name = r['template_name']
            x = int(r['x'])
            y = int(r['y'])
            t = self.parent.find_template_named(name)
            if t is not None:
######
                print 'map_reference_output_connections: ', t.as_node_url()
                tdn = self.get_template_definition_node(template_name)
                self._output_connections.update(t._map_output_connections(x,y,tdn))
    def resolve_inputs(self): #4th phase of startup
        #for each template in the drawing, track down the input values/nodes
        for n in self.children_nodes():
            if isinstance(n, (TemplateInstanceNode, MacroTemplateInstanceNode,)):
                n.resolve_inputs()
    def _init_connections(self):
        def filt_begin(el):
            return el['type']=='begin'
        def filt_end(el):
            return el['type']=='end'
        def map_xy(el):
            return (int(el['x']), int(el['y']))
        #prepare connections map
        self._connections = {} #keyed by end that connects to inputs
        begin = None
        end = None
        if self.debug: print self.name, ' init connections'
        self._connections = \
            dict(zip(map(map_xy, filter(filt_begin, self.connections)), \
                     map(map_xy, filter(filt_end, self.connections))))
        
        # for c in self.connections: #list of connection descriptors
            # type = c['type']
            # if type == 'begin':
                # begin = (int(c['x']), int(c['y']),)
            # elif type == 'end':
                # end = (int(c['x']), int(c['y']),)
                # if begin:
                    # self._connections[begin] = end
                    # if self.debug: print 'connection: ', str(begin), '  ', str(end)
            #else it is a corner
        
    def _init_constants(self):
        def map_xy(el):
            return (int(el['x']), int(el['y']))
        def map_value(el):
            return float(el['value'])
        self._constants = {} #keyed by x,y of connect point
        if self.debug: print self.name, ' init constants'
        self._constants = \
            dict(zip(map(map_xy, self.constants), map(map_value, self.constants)))
        # for c in self.constants:
            # self._constants[(int(c['x']), int(c['y']),)] = float(c['value'])
    def get_template_definition_node(self, name):
        return self.parent.get_template_definition_node(name)
    def find_connection_to(self, x_y): #called from template.  Drawing relative xy template input point
        try: #translate connection position
            x_y = self._connections[x_y] #get other end of connection line
        except:
            pass #almost all inputs use a connect line so exceptions are seldom
        #search all drawing elements for connection to x_y
        #check constants for match
        if x_y in self._constants:
            return self._constants[x_y]
        #search for another template in this drawing  or a referece to a template in another drawing that has an output that matches
        if x_y in self._output_connections:
            return self._output_connections[x_y]
        return None
    def generate_run_list(self): #answer a list of templates in run-order
        self._run_list = []
        compare=lambda a,b:cmp(a.position(),b.position())
        nodes = self.children_nodes()
        nodes.sort(compare)
        for n in nodes:
            if isinstance(n, MacroTemplateInstanceNode):
                self._run_list.extend(n.generate_run_list())
                continue #the macro will test true for the next line too so skip
            if isinstance(n, TemplateInstanceNode):
                self._run_list.append(n)
        return self._run_list
    def get_app(self):
        return self.parent
    def get_templates(self): #answer a list of templates on this drawing
        answer = []
        nodes = self.children_nodes()
        for n in nodes:
            if isinstance(n, (MacroTemplateInstanceNode, TemplateInstanceNode)):
                answer.append(n)
        return answer
    def graphic_width(self):
        x = 0
        for n in self.children_nodes():
            if hasattr(n, 'x'):
                x = max(x, n.x)
        return x + 100 #add in template graphic width?
    def graphic_height(self):
        y = 0
        for n in self.children_nodes():
            if hasattr(n, 'y'):
                y = max(y, n.y)
        return y + 100 #add in template graphic height?
    def as_html(self, live=1):
        return as_html.app_drawing_to_html(self, live)
    def _has_cov(self):
        # this controls child templates use of cov
        # but this node itself has no value
        return self.parent._has_cov()
        
class TemplateInstanceNode(CompositeNode, EventProducerMixin):
    def __init__(self):
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
        self.definition = None #name or url of definition.  If simple name, then relative to App node/template_library
        self.x = None #x,y location of insertion point of template inside drawing or macro
        self.y = None
        self._outputs = [] #Runtime List of output float values
        self.outputs = self._outputs #public list of output values
        self._output_connections = {} #x,y coords vs output nodes, used during "compile"
        self._input_map = {} #Dict of constants or nodes keyed by x,y coord 
        self._inputs = [] #Runtime list of inputs
        self._input_hotspots = [] #basically == _input_map.keys()
        self._definition_node = None
        self._mpx_get = None
        self._mpx_set = None
        self.__mpx_get_node = None
        self.__mpx_set_node = None
        self._override = 0
        self.last_exception = None
        self._bad_reference_counter = 0
        self.font = Font()
        self.allow_overrides = 'true'
        self.units = ''
        self.upper_alarm_threshold = 100
        self.upper_warning_threshold = 100
        self.lower_warning_threshold = 0
        self.lower_alarm_threshold = 0
        self._mpx_get_last_cov = None
        self.persistent = 0
        self.mpxset_error = 0
        self._set_mpx_pending = 0 #flag to prevent excessive queuing of sets
        self._set_mpx_last_value = None #last mpx_set value written.
        self.last_run_time = None
        #since None will not match ANY template value, at least one set runs
    def configure(self, config):
        set_attribute(self, 'debug', 0, config, int)
        set_attribute(self, 'x', None, config, int)
        set_attribute(self, 'y', None, config, int)
        set_attribute(self, 'definition', REQUIRED, config, str)
        set_attribute(self, 'persistent', 0, config, int)
        CompositeNode.configure(self, config)
        self.url = self.as_node_url()
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'x', config, str)
        get_attribute(self, 'y', config, str)
        get_attribute(self, 'definition', config, str)
        get_attribute(self, '_outputs', config, str)
        get_attribute(self, '_input_map', config, str)
        get_attribute(self, 'last_exception', config, str)
        get_attribute(self, 'persistent', config, str)
        if self.definition == 'mpxset':
            get_attribute(self, 'mpxset_error', config, str)
        return config
    def start(self):
        self.rpn = self.parent.rpn
        #generate self._outputs list from config info
        self._definition_node = self.parent.get_template_definition_node(self.definition) #get a reference to the definition for this node 
        try:
            if self._definition_node.name[:6] == 'mpxget':
                url = self.name
                url = url.replace(':','/')
                self._mpx_get = url.replace('~', self.parent.name) #this allows mpx gets and sets inside macros to use the macros name in the link url
            if self._definition_node.name[:6] == 'mpxset':
                url = self.name
                url = url.replace(':','/')
                self._mpx_set = url.replace('~', self.parent.name)
        except:
            msglog.exception()            
        self._definition_node.start() # we need to make sure the Definition node has started before we do this stuff 
        self.persistent = self.persistent or self._definition_node.is_persistent() or (self.name.find('.pv') >= 0) #templates named *.pv are presistent
        #self._outputs = [] #initialize the outputs registers
        #append = self._outputs.append
        #[append(0.0) for o in self._definition_node.outputs]
        self._outputs = array('f',[0.0]*len(self._definition_node.outputs))
        self.outputs = copy(self._outputs) #[:]
        try:
            if not self.has_child("_status"):
                status = TemplateStatusNode()
                status.configure({'name':'_status', 'parent':self})
        except:
            msglog.exception()
        # we use weakref's to children nodes to aid pruning
        try:
            self._status = weakref.proxy(self.get_child("_status"))
        except:
            msglog.exception()
        # output_nodes is a dictionary keyed by an integer of weak references
        # to child outputs nodes used to register for COV events
        self.output_nodes = {} 
        CompositeNode.start(self)
        #init outputs to 0 
        #TODO Persistent Output values
    def stop(self):
        CompositeNode.stop(self)
        # clear out references to other nodes to assist pruning
        self._mpx_get = None
        self._mpx_set = None
        #self._mpx_get_sid = None
        self.__mpx_get_node = None
        self.__mpx_set_node = None
        # delete weak ref
        self.output_nodes = None # release dictionary
        self._status = None
    def position(self):
        return (self.x, self.y)
    def map_output_connections(self):
        #generate a Dict for output connection x,y points vs output nodes for this template
        self._output_connections = self._map_output_connections(self.x, self.y)
        if self.debug:
            print self.name, ' output connection map: ', str(self._output_connections)
        return self._output_connections
    def _map_output_connections(self, offset_x, offset_y, tdn=None):
        output_connections = {}
        for n in self.children_nodes(): #output register nodes
            if isinstance(n, TemplateOutputNode):
                x,y = self._definition_node.get_output_x_y_at_index(n.index)
                if (x,y) > (0,0): #this output register is used as a connection point
                    x = x + offset_x #add in the offset for this template
                    y = y + offset_y
                    output_connections[(x,y)] = n
        return output_connections
    def resolve_inputs(self): #resolve Input sources
        self._input_map = {} #keyed by relative x,y, contains node reference or constant
        for x,y in self._definition_node.input_hotspots():
            node_or_constant = self.parent.find_connection_to((x + self.x, y + self.y,))
            if node_or_constant is None:
                if self._bad_reference_counter == 0: #do this only once at startup
                    msglog.log('Graphical Control', self.url, 'unconnected input for location: %d @ %d' % (x,y))
            if type(node_or_constant) == IntType:
                node_or_constant = float(node_or_constant)
            self._input_map[(x,y)] = node_or_constant
        inputs = []
        for xy in self._definition_node._inputs: #list of xy in step order
            inputs.append(self._input_map[xy])
        self._inputs = tuple(inputs)
        if self.debug: print self.name, ' resolved inputs: ', str(self._input_map)
    def get_input(self, hxy):
        try:
            input_value = self._inputs[hxy]
            if type(input_value) == FloatType:
                return input_value
            elif input_value: #must be node or error
                got = input_value.get()
                if got is not None: 
                    return float(got)
                return 0.0
            #try to find a node for a bad connection.  It may have been created after we started.
            self._bad_reference_counter += 1
            if self._bad_reference_counter > 113: #some prime number to keep this from consuming too much time
                self._bad_reference_counter = 1 #so we do not keep logging unconnected inputs.  see resolve_inputs above
                self.parent.map_reference_output_connections()
                self.resolve_inputs()
                if self._inputs[hxy] is not None:
                    print 'found reference for: ', self.url, ' input location: ', str(hxy)
        except:
            msglog.exception()
            pass
        return 0.0 #unconnected inputs default to 0.0
    def get_outputs(self): #return the list of output values
        return self._outputs
    def get_output(self, index): #used by rpn so leave as local copy of outputs
        return self._outputs[index]
    def set_output(self, index, value):
        if value is None or (value == 'None'):
            self._override = 0
        else:
            self._override = 1
            v = float(value)
            self._outputs[index] = v
            self.outputs[index] = v # to aid mpx_get since outputs are not updated after override
        self.get_app().new_override(self) #trigger update of persistant override data
    def get(self, skipcache=1):
        return self.outputs[0]
    def set(self, value):
        #this is usually called for a user override.
        #typically other nodes or periodic drivers will not be setting this
        # way because TIM pulls data, data is typically not pushed to it
        old_value = self.outputs[0]
        self.set_output(0, value)
        self.outputs[0] = self._outputs[0]
        new_value = self.outputs[0]
        # since the template node's value is the same as the first output
        # we need to trigger both events
        ref = self.output_nodes.get(0, None)
        if ref and ref(): # first output needs cov event trigger
            ref()._trigger_cov(new_value, old_value)
        self._trigger_cov(new_value, old_value) 
    def _set_mpx(self): #callback for mpx_set handling
        try:
            value = self._outputs[0] #get latest value
            # python 2.6 provides math.isnan(), < 2.6 we have
            # to otherwise ascertain this.  Purportedly, value != value
            # almost always works - to be safe we also do string match.
            if value != value and str(value).lower() == 'nan':
                value = None
            if is_overridable(self.__mpx_set_node):
                level = self.parent.parent.write_priority
                self.__mpx_set_node.override(value, level)
            else:
            	self.__mpx_set_node.set(value)
            self.mpxset_error = 0
        except Exception, e:
            if self.mpxset_error == 0 and self.get_app().debug:
                msglog.exception()
            self.last_exception = str(e)
            self.get_app()._exception_list.append((self.url, '_set_mpx',))
            self.mpxset_error = 1 #force another attempt
        self._set_mpx_last_value = value #for comparison with template value
        self._set_mpx_pending = 0 #allow another call to this method
        return
    def get_output_index(self, name):
        return self._definition_node.get_output_index(name)
    def output_hotspots(self):
        if self._output_hotspots is None:
            self._output_hotspots = self._definition_node.output_hotspots((self.x, self.y,))
        self._output_hotspots
    def input_hotspots(self):
        if self._input_hotspots is None:
            self._input_hotspots = self._definition_node.input_hotspots((self.x, self.y,))
        self._input_hotspots
    def move(self, offset=None): #the template has been moved
        self._output_hotspots = None #reset the hotspot lists
        self._input_hotspots = None
        if offset is not None:
            self.x = offset[0]
            self.y = offset[1]
    def _run_template_(self):
        if self._override:
            self.last_run_time = None
            return #don't process steps while in override
        try:
            start = uptime.secs()
            self.rpn.run(self._definition_node,self)
            self.last_run_time = uptime.secs() - start
        except Exception, e:
            self.last_exception = str(e)
            self.get_app()._exception_list.append((self.url, self.rpn.step_number,))
            if self.get_app().debug or self.get_app().first_run(): 
                msglog.exception()
                msglog.log('control service', 'run template exception', 'app: %s template: %s step: %s' % (self.get_app().name, self.url, self.rpn.step_number))
    def _run_trimmer_(self):
        if self._override:
            self.last_run_time = None
            return #don't process steps while in override
        self._outputs[0] = self.get_input(0)   
    def _run_template(self):
        self._run_template_()
        if self.outputs != self._outputs: #change of value
            old_outputs = self.outputs # save for event 
            self.outputs = copy(self._outputs) #[:]
            if self.persistent:
                self.get_app().new_persistent_value(self)
            self._trigger_covs(self.outputs, old_outputs)
    # methods to support EventProducer mixin
    def _trigger_covs(self, new_values, old_values):
        index = 0
        for new_value, old_value in zip(new_values, old_values):
            if new_value != old_value: # prevent needless events for unchanging value
                ref = self.output_nodes.get(index, None)
                if ref:
                    node = ref() # weak reference to output node
                    if node:
                        node._trigger_cov(new_value, old_value)
                        if index == 0: # handle our local copy of the output 0
                            self._trigger_cov(new_value, old_value)
            index += 1
    ## these next two methods handle cov events for this node's copy of output 0
    def _trigger_cov(self, new_value, old_value):
        cov_event = ChangeOfValueEvent(self, old_value, \
                    new_value, uptime.secs())
        self.event_generate(cov_event)
        self._status._trigger_cov(self._status.get(), None) # update child
    def event_subscribe(self, *args): # called for a new event subscription
        EventProducerMixin.event_subscribe(self, *args)
        # trigger initial value update to get things started
        self._trigger_cov(self.value, None)
    def has_cov(self):
        return self.parent._has_cov() # app and drawing nodes do not have cov
    def _run_mpx_get(self):
        if self._override: 
            return #don't process steps while in override
        self._run_template_() #it would be nice to put this after the mpx get to allow acting on the data retrieved but currently that would just copy over the result
        try:
            if self.__mpx_get_node is None: #this will tolerate missing nodes for mpx get and bind to them once they show up
                self.__mpx_get_node = as_node(self._mpx_get) #trigger discover if needed
                self.get_app().subscribe(self, self.__mpx_get_node)
                self._mpx_get_last_cov = self._outputs[0] #default value
            if isinstance(self._mpx_get_last_cov, Exception): #special handling for exceptions
                self._outputs[0] = self.outputs[0] #preserve old value
                self.last_exception = str(self._mpx_get_last_cov)
                if len(self._outputs) > 1:
                    self._outputs[1] = 1.0 #exception is active
            else:
                # markeva: float() allows for floats, ints, Booleans AND valid
                #          repr()s of those.
                self._outputs[0] = float(self._mpx_get_last_cov)
                if len(self._outputs) > 1:
                    self._outputs[1] = 0.0 #all is good
        except Exception, e:
            self.last_exception = str(e)
            self.get_app()._exception_list.append((self.url, self.rpn.step_number,))
            if self.get_app().debug: 
                msglog.exception()
                msglog.log('control service', 'run mpx get exception', 'app: %s template: %s link: %s' % (self.get_app().name, self.name, self._mpx_get))
            self._outputs[0] = self.outputs[0]  #leave answer as default value
            if len(self._outputs) > 1:
                self._outputs[1] = 1.0
        self.outputs = copy(self._outputs) #[:]
    def _mpx_get_cov_event_handler(self, answer):
        if self.get_app().debug:
            print self.url, ' : ', str(answer)
        if isinstance(answer, dict):
            answer = answer['value'] 
        self._mpx_get_last_cov = answer
    def _run_mpx_set(self):
        last_value = self._outputs[0]
        self._run_template_()
        try:
            try:
                trigger = self._outputs[1]
            except:
                trigger = 0
            if self.__mpx_set_node is None:
                self.__mpx_set_node = as_node(self._mpx_set)
                trigger = 1
            if ((str(self._outputs[0]) != str(self._set_mpx_last_value)) or \
               trigger or \
               self.mpxset_error) and \
               not self._set_mpx_pending: #COV has occured
                self._set_mpx_pending = 1
                thread_pool.NORMAL.queue_noresult(self._set_mpx) 
        except Exception, e:
            self.last_exception = str(e)
            self.get_app()._exception_list.append((self.url, 
                self.rpn.step_number,))
            self.__mpx_set_node = None #this will force as_node to run again to deal with disappearing nodess
            if self.debug or self.get_app().first_run(): 
                msglog.exception()
                msglog.log('control service', 'run mpx set exception', 'app: %s template: %s link: %s' % (self.get_app().name, self.name, self._mpx_set))
        self.outputs = copy(self._outputs) #[:]
    def _run(self):
        if self._mpx_get:
            self._run = self._run_mpx_get
        elif self._mpx_set:
            self._run = self._run_mpx_set
        else:
            self._run = self._run_template
        if self.definition == 'trimmer':
            self._run_template_ = self._run_trimmer_
        return self._run()
    def get_app(self):
        return self.parent.get_app()
    def get_override_status(self):
        return self._override
    def graphic_name(self):
        return self._definition_node.graphic_name()
    def graphic_height(self):
        return self._definition_node.graphic_height()
    def graphic_width(self):
        return self._definition_node.graphic_width()
class AlarmTemplateInstanceNode(TemplateInstanceNode):
    __node_id__ = 'a51ebd09-b3b1-468d-9e2f-420120d8c4fa'
    def configure(self, config):
        TemplateInstanceNode.configure(self, config)
        set_attribute(self, 'email', None, config, str)
        set_attribute(self, 'message', None, config, str)
        self._alarm_node = None
    def configuration(self):
        config = TemplateInstanceNode.configuration(self)
        get_attribute(self, 'email', config, str)
        get_attribute(self, 'message', config, str)
        return config
    def trigger_alarm(self): #called from rpn function
        message = self.message
        if len(self._outputs) > 2: #check for filling in parameters
            #deal with any mismatch in the number of %'s vs the number of output registers
            param_cnt = len(self.message.split('%')) - 1 #number of parameters, maybe
            pct_cnt = len(self.message.split('%%')) - 1 #number of %%
            param_cnt = param_cnt - (pct_cnt * 2) #true number of parameters in format string
            params = self._outputs[2:]
            if len(params) > param_cnt: #there is a mismatch in the parameter count
                params = params[:param_cnt] #trim off excess values 
            elif len(params) < param_cnt:
                params = params + array('f',[0.0]*8)[:(param_cnt - len(params))] #zero fill the rest
            message = self.message % tuple(params)
        context = self._get_context()
        self.get_alarm_node().trigger(self, time.time(), context, message)
    def clear_alarm(self):
        context = self._get_context()
        self.get_alarm_node().clear(self, time.time(), context, 'CLEARED')
    def get_alarm_node(self):
        if self._alarm_node:
            return self._alarm_node
        manager = as_node('/services/Alarm Manager')
        if not manager.is_running():
            return None #try again later when the manager is running
        name = self.get_app().name + '_' + self.parent.name + '_' + self.name
        if not manager.has_child(name): #not previously created
            #need to create a new alarm node
            configurator = as_node('/services/network/http_server/Alarm Configurator')
            if not configurator.is_enabled():
                configurator = as_node('/services/network/https_server/Alarm Configurator')
            config = {'name': name,
                      'description': self.message}
            # Tell the Alarm Configurator to create and persist the alarm.
            configurator.create_alarm(config, 0, True) # runs secure
        self._alarm_node = manager.get_child(name)
        return self._alarm_node
    def _get_context(self):
        context = {}
        parameters = self._outputs[2:]
        for index,parameter in enumerate(parameters):
            context["parameter %d" % (index + 1)] = parameter
        return context
    def _run_template(self):
        if self.get_alarm_node() is None:
            return  #force creation of related alarm node
        return TemplateInstanceNode._run_template(self)  
class TrendTemplateInstanceNode(TemplateInstanceNode):
    __node_id__ = '9ac7b175-cdd2-4806-ac1a-56332796bc87'
    def configure(self, config):
        TemplateInstanceNode.configure(self, config)
        set_attribute(self, 'email', None, config, str)
        set_attribute(self, 'message', None, config, str)
        self._trend_node = None
        self._period = None
        self._last_trigger_time = None
    def configuration(self):
        config = TemplateInstanceNode.configuration(self)
        get_attribute(self, 'email', config, str)
        get_attribute(self, 'message', config, str)
        return config
    def trigger_log(self):
        # if you can't beat them , join them.  Turn a triggered log into a periodic log
        log_trigger = self._inputs[-2]
        if type(log_trigger) == FloatType: #constant number
            # this is a periodic log that was setup on the first run
            return
        # this is a non-periodic log that collects only when triggered
        collector = self.get_trend_node().periodic_log.collector
        collector.period = 0 #prevent any new periodic collections
        scheduled, collector._scheduled = collector._scheduled, None #atomic
        if scheduled is not None:
            try:
                scheduled.cancel()
            except:
                pass
        collector.go()
#
#
#            if self._last_trigger_time is None:
#                self._last_trigger_time = time.time()
#                return #on the next trigger, measure the time and create a log with that period
#            self._period = int(time.time() - self._last_trigger_time)
#            self._period = (self._period / 5) * 5 #force period to be multiple of 5 seconds
#            self._period = max(self._period, 15)
#            self._period = min(self._period, 86400)
#            self.get_trend_node()
#    def trigger_log1(self): #called from rpn function
#        try:
#            self.get_trend_node().periodic_log.collector.collect()
#            print "self.get_trend_node().periodic_log.collector.collect()"
#        except:
#            msglog.exception()
#            self._trend_node = None #force another attempt
    def get_trend_node(self):
        if self._trend_node:
            return self._trend_node
        manager = as_node('/services/Trend Manager/trends')
        if not manager.is_running():
            return None #try again later when the manager is running
        name = self.get_app().name + '_' + self.parent.name + '_' + self.name
        name = name.replace('-','_').replace('.','_').replace('/','_')
        if not manager.has_child(name): #not previously created
            #need to create a new trend  node
            points = []
            for n in self._inputs[:-3]: #skip past last three inputs, they control trend, not data inputs
                url = n.as_node_url()
                node_name = url.split('/')[-2]
                points.append({'node':url, 'name':node_name})
            preferences ={'width': 800, 
                          'points': [{'color': 16711680, 'y-axis': 1}, 
                                     {'color': 65280, 'y-axis': 1}, 
                                     {'color': 255, 'y-axis': 1}, 
                                     {'color': 16776960, 'y-axis': 1}, 
                                     {'color': 52224, 'y-axis': 1}, 
                                     {'color': 204, 'y-axis': 1}, 
                                     {'color': 13421568, 'y-axis': 1}, 
                                     {'color': 52428, 'y-axis': 1}, 
                                     {'color': 13369548, 'y-axis': 1}],
                         'title': self.name,
                         'background': {'color': 2041901},
                         'y-axes': [{'to': 'auto', 'map': {}, 'enable': 1, 'type': 'numeric', 'from': 'auto'},
                                    {'to': 'auto', 'map': {}, 'enable': 0, 'type': 'binary', 'from': 'auto'}],
                         'text': {'color': 13686232, 'fontname': 'Verdana', 'fontsize': 12},
                         'timespan': {'value': '1', 'unit': 'hours'},
                         'height': 600}
            if self._period is None:
                self._period = 86000 * 365 #default period of once per year
                # period may be adjusted by log trigger input if not constant
                log_trigger = self._inputs[-2]
                if type(log_trigger) == FloatType: #constant number
                    self._period = int(log_trigger)
            config = {'name': name,
                      'parent' : manager,
                      'description': self.message,
                      'period':self._period, #we trigger via call
                      'points':points,
                      'preferences':preferences}
            from mpx.service.trendmanager.trend import Trend
            trend = Trend()
            trend.configure(config)
            trend.start()
            manager.parent._persist_trend_configuration(trend)
            #not allowedtrend.periodic_log.maximum_size = int(self._inputs[-3])
            #trend.periodic_log.start()
            #configurator.update_pdo()
        self._trend_node = manager.get_child(name)
        return self._trend_node
    def _run_template(self):
        # force creation of related log node and test if ready
        # if TrendManager is not started yet, don't run
        if self.get_trend_node() is None:
            return 
        return TemplateInstanceNode._run_template(self)

#module level functions so that access to the schedule node may be synchronized   
sched_lock = Lock()
def get_schedule_reference(schedule_name, schedule):
    sched_lock.acquire()
    try:
        manager = as_node('/services/time/local')
        if not manager.has_child('TIM'):
            from mpx.service.schedule.scheduler import Schedules as ScheduleHolder
            sh = ScheduleHolder(dmtype=GC_NEVER)
            default = {'name': 'TIM',
                   'parent': '/services/time/local',
                   'source': 'ScheduleConfigurator', #lying
                   'description': ''}
            sh.configure(default)
            sh.start()
        else:
            sh = manager.get_child('TIM')
        assert sh.is_running(), 'Unexpected state - schedule holder must be running'
        if not sh.has_child(schedule_name):
            from mpx.service.schedule.scheduler import Scheduler as Schedule
            s = Schedule()
            default = {'name': schedule_name,
                   'parent': '/services/time/local/TIM',
                   'source': 'ScheduleConfigurator',
                   'description': ''}
            s.configure(default)
            s.start()
            s.set_summary(schedule, 1) #currently saves to local schedule pdo, not manager's pdo
        else:
            s = sh.get_child(schedule_name)
        s.prunable = False
    finally:
        sched_lock.release()
    return s

class TimeScheduleInstanceNode(TemplateInstanceNode):
    __node_id__ = '2d43c208-6381-4037-adad-0c4132eaa266'
    def configure(self, config):
        TemplateInstanceNode.configure(self, config)
        set_attribute(self, 'schedule', None, config, str)
        self._schedule_node = None
    def configuration(self):
        config = TemplateInstanceNode.configuration(self)
        get_attribute(self, 'schedule', config, str)
        return config
    def _run_template_(self):
        try:
            if self._override: return #don't process steps while in override
            sched = self.get_schedule()
            value = sched.get()
            if type(value) in types.StringTypes:
                value = value.lower()
                if value == 'on':
                    value = 1
                elif value == 'off':
                    value = 0
            value = float(value)
            self._outputs[0] = value
            try:
                next = sched.get_next() # ('hh:mm:ss', 'value')
                ss = next[0].split(':')
                h = int(ss[0])
                m = int(ss[1])
                s = 0
                if len(ss) == 3:
                    s = int(ss[2])
                self._outputs[1] = float((h*3600) + (m*60) + s)
                value = next[1]
                if type(value) in types.StringTypes:
                    value = value.lower()
                    if value == 'on':
                        value = 1
                    elif value == 'off':
                        value = 0
                self._outputs[2] = float(value)
            except:
                if self.get_app().debug or self.get_app().first_run(): 
                    msglog.exception()
                    msglog.log('control service', 'run schedule template exception', 'app: %s template: %s unable to find next schedule entry' % (self.get_app().name, self.url))
                self._outputs[1:3] = (0.0,0.0)
        except Exception, e:
            self.last_exception = str(e)
            self.get_app()._exception_list.append((self.url, 0,))
            if self.get_app().debug: 
                msglog.exception()
                msglog.log('control service', 'run template time clock exception', 'app: %s template: %s' % (self.get_app().name, self.name))
    def get_schedule(self):  #need to do the same thing here we did with alarms in terms of getting the ScheduleConfigurator to do all this
    	if self._schedule_node is None:
            schedule_name = 'RZSched_' + self.get_app().name + ':' + self.parent.name + ':' + self.name
            self._schedule_node = get_schedule_reference(schedule_name, self.schedule)
            self.get_app()._schedule_names[schedule_name] = self # used to detect orphaned schedules
        return self._schedule_node        
    def set_summary(self, schedule=None, save=1): #used by action invoke to force original schedule
        if schedule is None:
            schedule = self.schedule
        self.get_schedule().set_summary(schedule, save)

class TemplateOutputNode(CompositeNode, EventProducerMixin):
    def __init__(self):
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
        self._status = None
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'index', config,str)
        return config
    def start(self):
        self.index = self.parent.get_output_index(self.name)
        self.parent.output_nodes[self.index] = weakref.ref(self) # used for fast COV lookup 
        try:
            if not self.has_child("_status"):
                status = TemplateStatusNode()
                status.configure({'name':'_status', 'parent':self})
                self._status = weakref.proxy(status)
        except:
            msglog.exception()
        CompositeNode.start(self)
    def get(self, skipCache=1):
        return self.parent.outputs[self.index]
    def set(self, value):
        old_value = self.get()
        self.parent.set_output(self.index, value)
        self._trigger_cov(self.get(), old_value)
    def nodecmp(self, other_url): #to help nodebrowser sorting
        other = as_node(other_url)
        if isinstance(other,self.__class__):
            return cmp(self.index, other.index)
        return cmp(self.name,other.name)
    def get_override_status(self):
        return self.parent.get_override_status()
    def _trigger_cov(self, new_value, old_value):
        if new_value != old_value: # prevent needless events for unchanging value
            cov_event = ChangeOfValueEvent(self, old_value, \
                        new_value, uptime.secs())
            self.event_generate(cov_event)
            self._status._trigger_cov(self._status.get(), None) # update child
    def event_subscribe(self, *args): # called for a new event subscription
        EventProducerMixin.event_subscribe(self, *args)
        # trigger initial value update to get things started
        self._trigger_cov(self.get(), None)
    def has_cov(self):
        return self.parent.has_cov()

class TemplateStatusNode(CompositeNode, EventProducerMixin): #supports RZ monitoring
    def __init__(self):
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
    def get(self, skipCache=1):
        return {'value':self.parent.get(), 'status':self.parent.get_override_status()}
    def _trigger_cov(self, new_value, old_value): # only called by parent
        cov_event = ChangeOfValueEvent(self, old_value, \
                        new_value, uptime.secs())
        self.event_generate(cov_event)
    def event_subscribe(self, *args): # called for a new event subscription
        EventProducerMixin.event_subscribe(self, *args)
        # trigger initial value update to get things started
        self._trigger_cov(self.get(), None)
    def has_cov(self):
        return self.parent.has_cov()
#the template.obj file 
INPUT = 1
CONSTANT = 0
RPN = 2
class TemplateDefinitionNode(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.graphic = None #bitmap (or png)
        self.steps = [] #Config info, rpn or input x,y/links
        self.outputs = [] #Config info List of Dicts of output names and locations in fixed order
        self._output_map = {} #Dict keyed by output name of config info
        self._outputs_x_y = {} #Dict keyed by x,y coord of config info
        self._inputs_x_y = {} #Dict keyed by x,y coord of input step config info
        self._inputs = [] #list of XY locations of inputs. index vs xy is put in t _ste-
        self.description = None #text
        self.__started = 0
        self._python_prim = None #used by Python primitive
    def configure(self, config):
        set_attribute(self, 'debug', 0, config, int)
        CompositeNode.configure(self, config)
        #outputs is a list of Dicts{'name':name, 'x':x or None, 'y': y or None}
        set_attribute(self, 'outputs', REQUIRED, config)
        self._init_outputs() #need to do this before init steps so they can find their outputs for rcl=>, etc
        #steps is list of Dicts {'rpn':step_text, 'x':x or None, 'y': y or None}
        set_attribute(self, 'steps', REQUIRED, config)
        #mime encoded PNG?
        set_attribute(self, 'graphic', None, config)
        set_attribute(self, 'description', None, config, str)
        self._init_steps(self.parent.parent.rpn)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'steps', config)
        get_attribute(self, 'outputs', config)
        get_attribute(self, 'graphic', config)
        get_attribute(self, 'description', config, str)
        get_attribute(self, '_output_map', config, str)
        get_attribute(self, '_outputs_x_y', config, str)
        get_attribute(self, '_inputs_x_y', config, str)
        return config
    def start(self):
        if not self.__started: #we may get started early by one of our TemplateInstance clients
            CompositeNode.start(self)
        self.__started = 1
    def _init_steps(self, rpn):
        #pre-compile the rpn steps to save time when running templates
        self._steps=[] #list of functions calls
        self._inputs_x_y = {}
        self._inputs = []
        i = 0
        index = 0 #inputs index
        for s in self.steps: #convert the config info into rpn call
            i += 1
            x = s['x']
            if x is None: x = 0
            x = int(x)
            y = s['y']
            if y is None: y = 0
            y = int(y)
            func = s['rpn'] #string from template step
            if x > 0 or y > 0: #must be input
                self._inputs_x_y[(x,y)] = s
                self._inputs.append((x,y))
                self._steps.append((INPUT, index, None)) #tuple indicates Input step
                index += 1
                continue
            try:
                self._steps.append((CONSTANT, float(func), None)) #throw exception if not float number
                continue
            except: #since not input or constant, look for function
                if func in rpn.RPN_functions: #step found
                    self._steps.append((RPN, get_function(func), None))
                    try:
                        if func == 'Python': #pure python template
                            statements = self.description.replace('\\n','\n') + '\n'
                            self._python_prim = compile(statements, '', 'exec')
                    except:
                        msglog.exception()
                    continue
                funcs = func.split() #check for multi-word RPN statements
                if funcs[0] in rpn.RPN_functions:
                    if funcs[0] in ('rcl=>','sto=>','shove=>','sum=>'):
                        self._steps.append((RPN, get_function(funcs[0]), self.get_output_index(func[len(funcs[0])+1:]),)) #name of register is everything to the right of the keyword
                        continue
                    if funcs[0] in ('goto=>','bit'):
                        self._steps.append((RPN, get_function(funcs[0]), int(funcs[1]),))
                        continue
                    #this is where to handle SNVT rpn statements
                raise EInvalidValue('control',self.as_node_url(), 'RPN Error in step %d with text %s' % (i - 1, func))
        self._steps = tuple(self._steps)
        self._inputs = tuple(self._inputs)
        if self.debug: print self.name, ' init_steps: ', str(self._steps)
    def _init_outputs(self):
        self._output_map = {} #Dict keyed by name
        self._outputs_x_y = {} #Dict keyed by x,y coords
        i = 0 #index
        for o in self.outputs: #convert the config info into run time data
            o['index'] = i #add index field to Output config info
            i += 1
            n = o['name']
            self._output_map[n] = o
            x = o['x']
            if x is None: x = 0
            y = o['y']
            if y is None: y = 0
            if x > 0 and y > 0: #must be input
                self._outputs_x_y[(x,y)] = o
        if self.debug:
            print self.name, ' output_map: ', str(self._output_map)
            print '    output_x_y: ', str(self._outputs_x_y)

    def get_output_index(self, name):
        if name in self._output_map:
            return self._output_map[name]['index']
        try:
            index = int(name)
            if index > 0 and index <= len(self._output_map): return index - 1
        except:
            pass
        msglog.log("control service", "error", "unable to find output register.  Template: %s, Register: %s" % (self.name, str(name)))
        return None
    def get_output_x_y(self, name):
        index = self.get_output_index(name)
        if index is not None:
            return self.get_output_x_y_at_index(index)
        None
    def get_output_x_y_at_index(self, index):
        o = self.outputs[index]
        return (int(o['x']), int(o['y']),)
    def stop(self):
        self.__started = 0
        CompositeNode.stop(self)
    def output_hotspots(self, offset=None):
        if offset is None:
            offset = (0,0)
        _x, _y = offset
        hotspots = [(x+_x, y+_y,) for x,y in self._outputs_x_y.keys()]
        return hotspots
    def input_hotspots(self, offset=None):
        if offset is None:
            offset = (0,0)
        _x, _y = offset
        hotspots = [(x+_x, y+_y,) for x,y in self._inputs_x_y.keys()]
        return hotspots
    def _run(self, node):
        node.rpn.run(self, node)
    def graphic_name(self):
        return self.name.replace('.','_') + '.png'
    def graphic_height(self):
        if self.graphic is None:
            self.get_graphic()
        return self.graphic.height
    def graphic_width(self):
        if self.graphic is None:
            self.get_graphic()
        return self.graphic.width
    def get_graphic(self):
        self.graphic = Graphic(self.graphic_name())
    def is_persistent(self):
        return self.name.find('.pv') >= 0
class MacroTemplateInstanceNode(TemplateInstanceNode):
    def start(self):
        self.rpn = self.parent.rpn
        #generate self._outputs list from config info
        self._definition_node = self.parent.get_template_definition_node(self.definition) #get a reference to the definition for this node 
        self._definition_node.start() # we need to make sure the Definition node has started before we do this stuff       
        try:
            if not self.has_child("_status"):
                status = self.TemplateStatusNode(self)
                status.configure({'name':'_status', 'parent':self})
        except:
            msglog.exception()
        CompositeNode.start(self)
    def get_app(self):
        return self.parent.get_app()
    def map_output_connections(self): #2nd phase of startup
        #generate a Dict for x,y vs nodes for this macro and return it to the drawing
        self._macro_output_connections = {} #key: (x,y), value: node
        #for each template or macro in this drawing, generate a map of outuput connection points
        for n in self.children_nodes():
            if isinstance(n, (TemplateInstanceNode, MacroTemplateInstanceNode,)): #only for the templates/macros, skip other nodes
                self._macro_output_connections.update(n.map_output_connections()) #recursive for macros
        #now translate any outputs that are used for connections external to this macro (the symbol connections)
        self._output_connections = self._definition_node.map_outputs_for(self._macro_output_connections, (self.x, self.y))
        return self._output_connections
    def map_reference_output_connections(self):
        self.parent.map_reference_output_connections()
    def resolve_inputs(self): #4th phase of startup
        #for each template in the drawing, track down the input values/nodes
        for n in self.children_nodes():
            if isinstance(n, (TemplateInstanceNode, MacroTemplateInstanceNode,)):
                n.resolve_inputs()
    def find_connection_to(self, x_y): #returns a reference to a node or constant
        if x_y in self._definition_node._connections: #translate connection position
            x_y = self._definition_node._connections[x_y] #get other end of connection line
        #search all drawing elements for connection to x_y
        #check constants for match
        if x_y in self._definition_node._constants:
            return self._definition_node._constants[x_y] #return a constant number
        #search for another template in this drawing  or a referece to a template in another drawing that has an output that matches
        if x_y in self._macro_output_connections:
            return self._macro_output_connections[x_y]
        #look at Input TAG lines to map xy into symbol coords
        if x_y in self._definition_node._inputs_x_y:
            x,y = self._definition_node._inputs_x_y[x_y] #translate into parent drawing coords
            return self.parent.find_connection_to((x + self.x, y + self.y,))
        return None
    def generate_run_list(self): #answer a list of templates in run-order
        self._run_list = []
        nodes = self.children_nodes()
        filt = lambda a: a.__class__ != TemplateStatusNode 
        nodes = filter(filt, nodes)
        compare=lambda a,b:cmp(a.position(),b.position())
        nodes.sort(compare)
        for n in nodes:
            if isinstance(n, MacroTemplateInstanceNode):
                self._run_list.extend(n.generate_run_list())
                continue
            if isinstance(n, TemplateInstanceNode):
                self._run_list.append(n)
        return self._run_list
    def get_template_definition_node(self, name):
        return self.parent.get_template_definition_node(name)

    def get(self, skipCache=1):
        return self._run_list[-1].get() #last tempate to run in the macro is the default output
class MacroTemplateDefinitionNode(DrawingNode):
    def __init__(self):        
        DrawingNode.__init__(self)
        self.graphic = None #bitmap (or png)
        #[{'name':Name of inner instance, 'template': name of template definition, 'x':x, 'y':y},]
        self.definitions = [] #List of Dict of Templates inside macro Config info
        #the "tag IO" lines
        #[{'symbol_x':int, 'symbol_y':int, 'drawing_x':int, 'drawing_y':int},]
        self.outputs = [] #Config info List of Dicts of output location and coord of template output it connects with
        self.inputs = [] #Config info List of Dicts of input location and coord of template input it connects with
        #I/O keyed from macro symbol connect points to templates inside drawing
        self._outputs_x_y = {} #Dict keyed by symbol output location, value is xy of inner template output
        self._inputs_x_y = {} #Dict keyed by x,y coord inner template input connect point, value is symbol input xy location
        self.__started = 0
    def configure(self, config):
        set_attribute(self, 'debug', 0, config, int)
        set_attribute(self, 'definitions', REQUIRED, config)
        self._init_definitions()
        set_attribute(self, 'outputs', REQUIRED, config)
        self._init_outputs()
        set_attribute(self, 'inputs', REQUIRED, config)
        self._init_inputs()
        #mime encoded PNG?
        set_attribute(self, 'graphic', None, config)
        set_attribute(self, 'description', None, config, str)
        DrawingNode.configure(self, config)
    def configuration(self):
        config = DrawingNode.configuration(self)
        get_attribute(self, 'outputs', config)
        get_attribute(self, 'graphic', config)
        get_attribute(self, 'inputs', config)
        return config
    def start(self):
        if not self.__started: #we may get started early by one of our TemplateInstance clients
            self._definitions = {} #convert
            CompositeNode.start(self)
        self.__started = 1
    def _init_definitions(self):
        self._definitions = {} #Dict keyed by name of template
        for t in self.definitions:
            self._definitions[t['name']]=t
    def _init_outputs(self):
        self._outputs_x_y = {} #Dict keyed by x,y coords
        i = 0 #index
        for o in self.outputs: #convert the config info into run time data
            sx = int(o['symbol_x'])
            sy = int(o['symbol_y'])
            dx = int(o['drawing_x'])
            dy = int(o['drawing_y'])
            #keyed by symbol xy, value is drawing xy
            self._outputs_x_y[(sx,sy)] = (dx,dy)
    def _init_inputs(self):
        self._inputs_x_y = {} #Dict keyed by x,y coords
        i = 0 #index
        for o in self.inputs: #convert the config info into run time data
            sx = int(o['symbol_x'])
            sy = int(o['symbol_y'])
            dx = int(o['drawing_x'])
            dy = int(o['drawing_y'])
            #keyed by drawing xy, value is symbol xy (opposite of outputs map)
            self._inputs_x_y[(dx,dy)] = (sx,sy)
    def stop(self):
        self.__started = 0
        CompositeNode.stop(self)
    def output_hotspots(self, offset=None):
        if offset is None: offset = (0,0)
        _x, _y = offset
        hotspots = []
        for x,y in self._outputs_x_y.keys():
            hotspots.append((x+_x, y+_y,))
        return hotspots
    def input_hotspots(self, offset=None):
        if offset is None:
            offset = (0,0)
        _x, _y = offset
        hotspots = []
        for x,y in self._inputs_x_y.values():
            hotspots.append((x+_x, y+_y,))
        return hotspots
    def map_outputs_for(self, instance_connections, offset=None):
        if offset is None: offset = (0,0)
        _x, _y = offset
        answer = {}
        for x_y in self._outputs_x_y.keys():
            if self._outputs_x_y[x_y] in instance_connections:
                n = instance_connections[self._outputs_x_y[x_y]] #get the node reference
                x,y = x_y
                answer[(x+_x, y+_y)] = n
        return answer #map of xy coords in macro instance's drawing vs the internal node.
    def graphic_name(self):
        return self.name + '.png'
    def graphic_height(self):
        if self.graphic is None:
            self.get_graphic()
        return self.graphic.height
    def graphic_width(self):
        if self.graphic is None:
            self.get_graphic()
        return self.graphic.width
    def get_graphic(self):
        self.graphic = Graphic(self.name)

class Font(object):
    def __init__(self, aFont=None):
        if aFont:
            self.weight = aFont.weight
            self.height = aFont.height
            self.width = aFont.width
            self.color_name = aFont.color_name
            self.italic = aFont.italic
            self.face_name = aFont.face_name
            self.background_color_name = aFont.background_color_name
        else:
            self.weight = 'normal'
            self.height = 14
            self.width = 8
            self.color_name = 'white'
            self.italic = 'normal'
            self.face_name = 'monospace'
            self.background_color_name = 'green'


class Graphic(object):
    def __init__(self, name):
        f=open('/var/mpx/www/http/template_images/'+name)
        f.seek(16) #width and height start at 16
        wh = f.read(8)
        f.close()
        w,h = struct.unpack('!LL', wh)
        self.height = h
        self.width = w
        self.name = name

