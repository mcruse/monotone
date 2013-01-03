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
import string
import time
from interfaces import ITrigger
from interfaces import IComparisonTrigger
from mpx.componentry import implements
from mpx.lib.neode.node import CompositeNode
from threading import Event as Flag
from mpx.lib.translator.calculator import Calculator
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.scheduler import scheduler
from mpx.lib.threading import Lock
from mpx.lib import msglog
from mpx.lib import EnumeratedValue
from mpx.lib.exceptions import EConfigurationIncomplete
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.eventdispatch import Event
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation

class TriggerEvent(Event):
    def __init__(self, trigger, timestamp, critical, context):
        super(TriggerEvent, self).__init__(trigger)
        self.timestamp = timestamp
        self.critical = critical
        self.context = context
    def get_trigger(self):
        return self.source
    def get_arguments(self):
        source = self.source
        if not isinstance(source, str):
            source = as_node_url(source)
        return (source, self.timestamp, self.context, self.critical)

class TriggerActivated(TriggerEvent):
    pass

class TriggerCleared(TriggerEvent):
    pass

class _Trigger(CompositeNode):
    implements(ITrigger)
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self, *args):
        self.targetmap = {}
        self.targets = set()
        self.unresolvable = set()
        self.synclock = Lock()
        super(_Trigger, self).__init__(*args)
    
    security.protect('get_targets', 'View')
    def get_targets(self, unresolved=False):
        #get targets
        targets = []
        for targeturl in self.targets:
            target = self.targetmap.get(targeturl)
            if target and not target.parent:
                message = "Trigger %s resetting pruned target: %r."
                msglog.warn(message % (self.name, targeturl))
                self.targetmap.pop(targeturl)
                target = None
            if not target:
                try:
                    target = self.nodespace.as_node(targeturl)
                except KeyError:
                    if targeturl not in self.unresolvable:
                        message = "Trigger %s Unable to resolve target: %r."
                        msglog.warn(message % (self.name, targeturl))
                    self.unresolvable.add(targeturl)
                else:
                    self.targetmap[targeturl] = target
                    self.unresolvable.discard(targeturl)
            if target:
                targets.append(target)
            elif unresolved:
                targets.append(targeturl)
        return targets
    
    security.protect('get_target_names', 'View')
    def get_target_names(self):
        return [target.name for target in self.get_targets()]
    
    security.protect('add_target', 'Configure')
    def add_target(self, target):
        if not isinstance(target, str):
            targeturl = as_node_url(target)
        else:
            targeturl = target
            try:
                target = self.nodespace.as_node(targeturl)
            except KeyError:
                target = None                
        if targeturl == "/":
            raise ValueError("Invalid trigger target: %r" % target)
        self.synclock.acquire()
        try:
            if targeturl not in self.targets:
                self.targets.add(targeturl)
                if target:
                    self.targetmap[targeturl] = target
                else:
                    message = "Trigger %r added unresolvable target: %r"                    
                    msglog.warn(message % (self.name, targeturl))
                added = True
            else:
                added = False
                message = "Trigger %r not adding target %r: already exists."
                msglog.warn(message % (self.name, targeturl))
        finally: 
            self.synclock.release()
        return added
    
    security.protect('remove_target', 'Configure')
    def remove_target(self, target):
        if not isinstance(target, str):
            targeturl = as_node_url(target)
        else:
            targeturl = target
        self.synclock.acquire()
        try: 
            self.targets.remove(targeturl)
        except KeyError:
            removed = False
            message = "Target %s not removed from %s: does not exist."
            msglog.warn(message % (target, self))
        else:
            try:
                self.targetmap.pop(targeturl)
            except KeyError:
                pass
            removed = True
            msglog.inform("Target %s removed from %s." % (target, self))
        finally: 
            self.synclock.release()
        return removed

class Calculated(_Trigger, Calculator):
    implements(ITrigger)

    INITIALIZING = EnumeratedValue(0,'init')
    INACTIVE=EnumeratedValue(1,'inactive')
    ACTIVE=EnumeratedValue(2,'active')
    ERROR=EnumeratedValue(3,'error')
    DISABLED=EnumeratedValue(4, 'disabled')
    STATES = {INITIALIZING:{'start':INACTIVE,'stop':DISABLED},
              INACTIVE:{'clear':INACTIVE,'trigger':ACTIVE,'stop':DISABLED},
              ACTIVE:{'clear':INACTIVE,'trigger':ACTIVE,'stop':DISABLED},
              ERROR:{'clear':INACTIVE,'trigger':ERROR,'stop':DISABLED},
              DISABLED:{'stop':DISABLED,'start':INACTIVE}}
    ACTIONS = ('clear', 'trigger')
    EVENTTYPES = {(ACTIVE, INACTIVE): TriggerCleared,
                  (INACTIVE, ACTIVE): TriggerActivated}

    def __init__(self, *args):
        _Trigger.__init__(self, *args)
        Calculator.__init__(self)
        self.state = self.INITIALIZING
        self.scheduled = None
        self._running = Flag()
        self._start_failed = False
    def configure(self,config):
        Calculator.configure(self, config)
        _Trigger.configure(self, config)
        message = ''
        if 'poll_period' in config:
            try:
                policy = float(config['poll_period'])
            except ValueError:
                raise ValueError('Value of field \'Poll period\' is not numeric')
        if not (config.has_key('message') and config['message']):
            for var in self.variables:
                if message: 
                    message += ', '
                message += '%s = ${%s}' % (var['vn'],var['vn'])
            set_attribute(self, 'message', message, {})
        else: 
            set_attribute(self, 'message', REQUIRED, config)
        set_attribute(self, 'poll_period', 2, config, float)
        set_attribute(self, 'critical_input', '', config)
        set_attribute(self, 'description', '', config)
        set_attribute(self, 'enabled', 1, config, as_boolean)
        self.manager = self.parent
    def configuration(self):
        config = Calculator.configuration(self)
        config.update(_Trigger.configuration(self))
        get_attribute(self,'message', config)
        get_attribute(self, 'poll_period', config, str)
        get_attribute(self, 'critical_input', config)
        get_attribute(self,'description', config)
        get_attribute(self, 'enabled', config, str)
        return config
    def is_active(self):
        return self.get_state() is self.ACTIVE
    def is_running(self):
        return self._running.isSet()
    def get_state(self):
        return self.state
    def get(self, skipCache=0):
        return str(self.get_state())
    def start(self):
        if not self._running.isSet():
            _Trigger.start(self)
            variables = []
            self._message = ''
            message = self.message
            while '$' in message:
                index = message.index('$')
                try:
                    if message[index+1] == '{':
                        end = string.find(message,'}',index)
                        if end > -1:
                            var = message[index:end+1]
                            variable = var[2:-1]
                            if '$' not in variable and '{' not in variable:
                                message = string.replace(message,var,'%s')
                                variables.append(variable)
                except IndexError:
                    pass
                self._message += message[0:index+1]
                message = message[index+1:]
            self._message += message
            self._message_vars = tuple(variables)
            self.state = self.STATES[self.state]['start']
            self._running.set()
        try:
            Calculator.start(self)
        except:
            message = "Failed to start Trigger %r.  Will retry in 30 secs."
            msglog.error(message % self.name)
            if not self._start_failed:
                msglog.exception(prefix="handled")
            self._start_failed = True
        else:
            message = "Trigger %r started.  Evaluation runs in 30 seconds."
            msglog.inform(message % self.name)
            self._start_failed = False
        finally:
            self.reschedule(30)
    def stop(self):
        self.synclock.acquire()
        try:
            self._running.clear()
            self.state = self.STATES[self.state]['stop']
        finally: 
            self.synclock.release()
        self.reschedule()
        Calculator.stop(self)
        _Trigger.stop(self)
    def __call__(self):
        if not self.started:
            self.start()
        else:
            try: 
                self._run_evaluation()
            except:
                msglog.exception()
                msglog.inform('Trigger reschedule delayed 20 seconds.')
                delay = 20
            else: 
                delay = self.poll_period
            finally:
                self.reschedule(delay)
    def _run_evaluation(self):
        values = self._get_values(self.local_context)
        current_value = self.evaluate(values)
        self.synclock.acquire()
        try:
            # Check running state before performing evaluation.
            if not self._running.isSet(): 
                return
            action = self.ACTIONS[current_value]
            previous = self.state
            self.state = current = self.STATES[self.state][action]
        finally: 
            self.synclock.release()
        eventtype = self.EVENTTYPES.get((previous, current))
        if not eventtype: 
            return
        timestamp = time.time()
        if self.critical_input:
            value = values[self.critical_input]
        elif len(values.keys()) == 1:
            value = values.values()[0]
        else: 
            value = None
        event = eventtype(self, timestamp, value, values)
        self._dispatch(event)
    def _dispatch(self, event):
        self.manager.dispatcher.dispatch(event)
    def reschedule(self, delay = None):
        scheduled, self.scheduled = self.scheduled, None
        if scheduled: 
            scheduled.cancel()
        if self._running.isSet():
            if delay is None:
                delay = self.poll_period
            self.scheduled = scheduler.after(
                delay, self.manager.queue_trigger, (self,))
        return self.scheduled

def Trigger(*args, **kw):
    """
        Factory method for reverse compatibility.
    """
    msglog.warn("Depcreated Trigger factory used: use Calculated instead.")
    return Calculated(*args, **kw)

class ComparisonTrigger(Calculated):
    implements(IComparisonTrigger)
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self, *args):
        Calculated.__init__(self, *args)
        self.deferred = None
    def configure(self, config):
        set_attribute(self,'comparison','',config)
        set_attribute(self, 'input', '', config)
        set_attribute(self, 'constant', '', config)
        if 'hysteresis' in config:
            try:
                policy = float(config['hysteresis'])
            except ValueError:
                raise ValueError('Value of field \'Hysteresis\' is not numeric')
        if 'alarm_delay' in config:
            try:
                policy = float(config['alarm_delay'])
            except ValueError:
                raise ValueError('Value of field \'Alarm delay\' is not numeric')
        set_attribute(self, 'hysteresis', 0.0, config, float)
        set_attribute(self, 'alarm_delay', 0.0, config, float)
        if self.hysteresis < 0:
            raise ValueError('Hysteresis value cannot be negative.')
        set_attribute(self, 'message', 'input is less than ${constant}', config)
        if self.comparison and self.input:
            if self.comparison in ('greater_than','>', 'input > constant'):
                self._comparison_operator = '>'
            elif self.comparison in ('less_than', '<', 'input < constant'):
                self._comparison_operator = '<'
            else:
                raise EConfigurationIncomplete('comparison')
            statement = 'input %s constant' % self._comparison_operator
            config['variables'] = [{'vn':'input','node_reference':config['input']},
                                   {'vn':'constant',
                                    'node_reference':config['constant']}]
            config['statement'] = statement
            config['critical_input'] = 'input'
        return Calculated.configure(self, config)
    
    security.protect('get_constant', 'View')
    def get_constant(self):
        return self.local_context['constant']
    security.protect('set_constant', 'Override')
    def set_constant(self,const):
        self.local_context['constant'] = const
    def configuration(self):
        config = Calculated.configuration(self)
        get_attribute(self,'comparison',config)
        get_attribute(self, 'input', config)
        get_attribute(self, 'constant', config)
        get_attribute(self, 'hysteresis', config, str)
        get_attribute(self, 'alarm_delay', config, str)
        return config
    def start(self):
        super(ComparisonTrigger, self).start()
        self._constant = float(self.constant)
    def stop(self):
        super(ComparisonTrigger, self).stop()
        self._constant = None
    def _dispatch(self, event):
        if self.hysteresis != 0:
            comparison = self._comparison_operator
            if isinstance(event, TriggerActivated):
                # Comarpsion is True
                if comparison == '>':
                    # Input is > constant
                    self.set_constant(self._constant - self.hysteresis)
                elif comparison == '<':
                    # Input is < constant
                    self.set_constant(self._constant + self.hysteresis)
                else: raise ValueError('Operator %s uknnown.' % comparison)
            elif isinstance(event, TriggerCleared):
                # Comparison is False, clear hysteresis
                self.set_constant(self._constant)
            else: raise TypeError('Event of unknown type.')
        if self.alarm_delay:
            self.synclock.acquire()
            try:
                if isinstance(event, TriggerActivated):
                    self.deferred = scheduler.after(self.alarm_delay, 
                                                    self._deferred_dispatch,
                                                    (event,))
                elif isinstance(event, TriggerCleared) and self.deferred:
                    scheduled, self.deferred = self.deferred, None
                    if scheduled:
                        scheduled.cancel()
                else:
                    super(ComparisonTrigger, self)._dispatch(event)
            finally: self.synclock.release()
        else:
            super(ComparisonTrigger, self)._dispatch(event)
    def _deferred_dispatch(self, event):
        self.synclock.acquire()
        try:
            if self.deferred:
                super(ComparisonTrigger, self)._dispatch(event)
                self.deferred = None
        finally: self.synclock.release()

class BoundTrigger(_Trigger):
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self, *args):
        self.source = None
        self._source = None
        self._source_clear = None
        self._source_trigger = None
        super(BoundTrigger, self).__init__(*args)
    def configure(self, config):
        self.source = config.get("source", self.source)
        return super(BoundTrigger, self).configure(config)
    def configuration(self):
        config = super(BoundTrigger, self).configuration()
        if self.source:
            config["source"] = self.source
        return config
    def start(self):
        if not self.is_running():
            self._source = as_node(self.source)
            if self._source.trigger.im_self is not self:
                self._source_trigger = self._source.trigger
            self._source.trigger = self.trigger
            if self._source.clear.im_self is not self:
                self._source_clear = self._source.clear
            self._source.clear = self.clear
        return super(BoundTrigger, self).start()
    def stop(self):
        if self._source:
            if self._source_trigger:
                self._source.trigger = self._source_trigger
            self._source_trigger = None
            if self._source_clear:
                self._source.clear = self._source_clear
            self._source_clear = None
        self._source = None
        return super(BoundTrigger, self).stop()
    
    security.protect('trigger', 'Override')
    def trigger(self, source, *args, **kw):
        result = self._source_trigger(source, *args, **kw)
        if not isinstance(source, str):
            source = as_node_url(source)
        for target in self.get_targets():
            try:
                target.trigger(source, *args, **kw)
            except:
                message = "%s failed to trigger target: %s."
                msglog.warn(message % (self, target))
                msglog.exception(prefix="handled")
        return result
    security.protect('trigger', 'Override')
    def clear(self, source, *args, **kw):
        result = self._source_clear(source, *args, **kw)
        if not isinstance(source, str):
            source = as_node_url(source)
        for target in self.get_targets():
            try:
                target.clear(source, *args, **kw)
            except:
                message = "%s failed to clear target: %s."
                msglog.warn(message % (self, target))
                msglog.exception(prefix="handled")
        return result






