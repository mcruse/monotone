"""
Copyright (C) 2002 2003 2005 2006 2008 2010 2011 Cisco Systems

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
import array
import string
import time
import urllib

from mpx.lib import EnumeratedValue
from mpx.lib import msglog

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.event import AlarmClearEvent
from mpx.lib.event import AlarmTriggerEvent
from mpx.lib.event import EventConsumerMixin
from mpx.lib.event import EventProducerMixin

from mpx.lib.exceptions import EConfigurationIncomplete
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENotStarted
from mpx.lib.exceptions import EUnreachableCode

from mpx.lib.msglog.types import ERR
from mpx.lib.msglog.types import INFO
from mpx.lib.msglog.types import WARN

from mpx.lib.node import ConfigurableNode
from mpx.lib.node import as_node

from mpx.lib.scheduler import scheduler

from mpx.lib.threading import Lock
from mpx.lib.threading import QueueFull

from mpx.lib.translator.calculator import Calculator

##
# @todo Add better error handling for resending.  Currently taken care of by 
#       the alarm exporter, much too tight of coupling.  Consider attatching 
#       state machine to alarm event to manage several simultaneous alarms.
class CalculatedTrigger(Calculator,EventProducerMixin):
    INITIALIZING = EnumeratedValue(0,'init')
    INACTIVE=EnumeratedValue(1,'inactive')
    TRIGGERED=EnumeratedValue(2,'triggered')
    SENDING=EnumeratedValue(3,'sending')
    SENT=EnumeratedValue(4,'sent')
    ACKNOWLEDGED=EnumeratedValue(5,'acknowledged')
    ERROR=EnumeratedValue(6,'error')
    DISABLED=EnumeratedValue(7, 'disabled')
    STATE = {INITIALIZING:{'start':INACTIVE,'stop':DISABLED},
             INACTIVE:{'start':INACTIVE,
                       'clear':INACTIVE,'trigger':TRIGGERED,'stop':DISABLED},
             TRIGGERED:{'start':ERROR,
                        'caught':SENDING,'stop':DISABLED},
             SENDING:{'start':ERROR,
                      'succeed':SENT,'fail':ERROR,'stop':DISABLED},
             SENT:{'start':SENT,
                   'clear':INACTIVE,'trigger':SENT,
                   'acknowledge':ACKNOWLEDGED,'stop':DISABLED},
             ACKNOWLEDGED:{'start':ACKNOWLEDGED,
                           'clear':INACTIVE,'trigger':ACKNOWLEDGED,
                           'acknowledge':ACKNOWLEDGED,'stop':DISABLED},
             ERROR:{'start':ERROR,
                    'clear':INACTIVE,'trigger':ERROR,'stop':DISABLED},
             DISABLED:{'start':INACTIVE,
                       'stop':DISABLED}}
    def __init__(self):
        Calculator.__init__(self)
        EventProducerMixin.__init__(self)
        self._state = self.INITIALIZING
        self._current_id = None
        self._scheduled = None
        self._state_lock = Lock()
        self._schedule_lock = Lock()
        self.require_acknowledge = 0
        return
    def get(self, skipCache=0):
        return int(self._state)
    def __str__(self):
        return '%s: %s' % (self.name, str(self._state))
    def configure(self,config):
        Calculator.configure(self, config)
        message = ''
        if not (config.has_key('message') and config['message']):
            for var in self.variables:
                if message:
                    message += ', '
                message += '%s = ${%s}' % (var['vn'],var['vn'])
            set_attribute(self, 'message', message, {})
        else:
            set_attribute(self, 'message', REQUIRED, config)
        set_attribute(self, 'poll_period', 0.1, config, float)
        set_attribute(self, 'critical_input', '', config)
        set_attribute(self, 'send_retries', 3, config, int)
        set_attribute(self, 'enabled', 1, config, as_boolean)
        set_attribute(self, 'require_acknowledge', 0, config, as_boolean)
        self._manager = self.parent.parent
    def configuration(self):
        config = Calculator.configuration(self)
        get_attribute(self,'message', config)
        get_attribute(self, 'poll_period', config, str)
        get_attribute(self, 'critical_input', config)
        get_attribute(self, 'send_retries', config)
        get_attribute(self, 'enabled', config, str)
        return config
    def enable(self):
        self.enabled = 1
        self.start()
    def disable(self):
        self.enabled = 0
        self.stop()
    def is_enabled(self):
        return self.enabled
    def get_state_name(self):
        return str(self._state)
    def start(self):
        self.STATE = {}
        self.STATE.update(self.__class__.STATE)
        if self.require_acknowledge:
            self.STATE[self.__class__.SENT]['clear'] = self.__class__.SENT
        Calculator.start(self)
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
        self._change_state('start')
    def stop(self):
        # this is where we need to cancel our schedule entry.
        self._change_state('stop')
        Calculator.stop(self)
    def caught(self,alarm):
        if alarm.__class__ == AlarmTriggerEvent:
            self._caught_trigger(alarm)
        elif alarm.__class__ == AlarmClearEvent:
            self._caught_clear(alarm)
    def success(self,alarm):
        self._change_state('succeed')
    def fail(self,alarm):
        msglog.log('broadway',msglog.types.WARN,
                   'Failed sending alarm -> %s' % alarm)
        self._change_state('fail')
    ##
    # @todo Consider creating and using an alarm ack event 
    #       similar to the way that trigger and clear are used. 
    #       This would allow the manager to keep a list of 
    #       'active' 'unacknowledged' alarms so that something 
    #       like the alarm handler could generate a list.
    def acknowledge(self,alarm=None):
        self._change_state('acknowledge')
    def state(self,alarm):
        return self._state
    def check_condition(self):
        try:
            values = self._get_values(self.local_context)
        except:
            msglog.exception()
            self._reschedule()
            return
        value = None
        if self.critical_input:
            value = values[self.critical_input]
        elif len(values.keys()) == 1:
            value = values.values()[0]
        if self._evaluate(values):
            self._trigger(time.time(),value,values)
        else:
            self._clear(time.time(),value,values)
    def _reschedule(self):
        self._schedule_lock.acquire()
        try:
            if (self._scheduled is None or 
                self._scheduled.executing() or
                self._scheduled.expired()):
                self._scheduled = scheduler.after(
                    self.poll_period,self._manager.queue_alarm_check,(self,))
        finally:
            self._schedule_lock.release()
        return
    def _have_trasition(self,action):
        self._state_lock.acquire()
        try:
            actions = self.STATE[self._state]
            return actions.has_key(action)
        finally:
            self._state_lock.release()
        raise EUnreachableCode()
    def _change_state(self,action):
        self._state_lock.acquire()
        try:
            actions = self.STATE[self._state]
            if not actions.has_key(action):
                raise EInvalidValue('action',action,
                                    'Invalid action from state %s' %
                                    self._state)
            state = actions[action]
            if self.TRANSITION[state]:
                self.TRANSITION[state](self)
            self._state = state
        finally:
            self._state_lock.release()
        return
    ##
    # @todo May want to add another state that waits for the 
    #       AlarmClearEvent to be confirmed caught, but then 
    #       again, maybe not.
    def _clear(self,timestamp,value,values):
        try:
            self._change_state('clear')
            # If the alarm is currently 'active'
            if (self._state == self.ACKNOWLEDGED or
                (self._state == self.SENT and not self.require_acknowledge)):
                if self._current_id != None:
                    clear = AlarmClearEvent(self,self._current_id,timestamp,
                                            value,values)
                    self._current_id = None
                    self.event_generate(clear)
                else:
                    msglog.log('broadway',msglog.types.WARN,
                               'IGNORING CLEAR BECAUSE NO CURRENT ID')
        except EInvalidValue:
            pass
    def _trigger(self,timestamp,value,values):
        try:
            state = self._state
            self._change_state('trigger')
            if state == self.INACTIVE:
                self._current_id = self._manager.unique_id()
                message = self._message
                for var in self._message_vars:
                    if values.has_key(var):
                        message = string.replace(message,'%s',str(values[var]),1)
                    else:
                        message = string.replace(message,'%s','${%s}' % var, 1)
                trigger = AlarmTriggerEvent(self,self._current_id,timestamp,
                                            value,values,message)
                self.event_generate(trigger)
        except EInvalidValue:
            pass
    def _caught_trigger(self,alarm):
        self._change_state('caught')
    def _caught_clear(self,alarm):
        pass
    TRANSITION = {INACTIVE:_reschedule,TRIGGERED:None,SENDING:None,
                  SENT:_reschedule,ACKNOWLEDGED:_reschedule,
                  ERROR:_reschedule,DISABLED:None}

class ComparisonTrigger(CalculatedTrigger):
    def configure(self, config):
        set_attribute(self,'comparison',REQUIRED,config)
        set_attribute(self, 'input', REQUIRED, config)
        if self.comparison in ('greater_than','>'):
            statement = 'input > constant'
        elif self.comparison in ('less_than', '<'):
            statement = 'input < constant'
        else:
            raise EConfigurationIncomplete('comparison')
        config['variables'] = [{'vn':'input','node_reference':config['input']},
                               {'vn':'constant',
                                'node_reference':config['constant']}]
        config['statement'] = statement
        config['critical_input'] = 'input'
        return CalculatedTrigger.configure(self, config)
    def get_constant(self):
        return self.local_context['constant']
    def set_constant(self,const):
        self.local_context['constant'] = const
    def configuration(self):
        config = CalculatedTrigger.configuration(self)
        get_attribute(self,'comparison',config)
        get_attribute(self, 'input', config)
        get_attribute(self, 'constant', self.local_context, str)
        return config

class EventTrigger(ConfigurableNode,EventProducerMixin,EventConsumerMixin):
    def __init__(self):
        ConfigurableNode.__init__(self)
        EventProducerMixin.__init__(self)
        EventConsumerMixin.__init__(self)
        self._current_id = None
        self._event_class = None
        self.start_counter = 0
        self.pnode_obj = None
        self.pnode_subscribed = 0
    #
    def configure(self,config):
        ConfigurableNode.configure(self, config)
        message = ''
        if not (config.has_key('message') and config['message']):
            for var in self.variables:
                if message:
                    message += ', '
                message += '%s = ${%s}' % (var['vn'],var['vn'])
            set_attribute(self, 'message', message, {})
        else:
            set_attribute(self, 'message', REQUIRED, config)
        set_attribute(self, 'subject', '', config, str)
        set_attribute(self, 'send_retries', 3, config, int)
        set_attribute(self, 'enabled', 1, config, as_boolean)
        set_attribute(self, 'prodnode', '', config, str)
        set_attribute(self, 'eventmodule', '', config, str)
        set_attribute(self, 'eventclass', '', config, str)
        set_attribute(self, 'debug', 0, config, int)
        self._event_class = None
         # Try to import our specified event class.
        try:
            x = __import__(self.eventmodule, {}, {}, self.eventclass)
            self._event_class = eval('x.%s' % self.eventclass)
        except:
            msglog.log('broadway',msglog.types.WARN,
                       'Got exception trying to import event class.')
            msglog.exception()
        self._manager = self.parent.parent
    #
    def configuration(self):
        config = ConfigurableNode.configuration(self)
        get_attribute(self, 'message', config)
        get_attribute(self, 'subject', config)
        get_attribute(self, 'send_retries', config)
        get_attribute(self, 'enabled', config, str)
        get_attribute(self, 'prodnode', config, str)
        get_attribute(self, 'eventmodule', config, str)
        get_attribute(self, 'eventclass', config, str)
        get_attribute(self, 'debug', config, int)
        return config
    ##
    # Log's the specified message with the specified type.
    #
    def _logMsg(self, type, msg):
        msglog.log('Event Alarm', type, msg) 
    def enable(self):
        self.enabled = 1
        self.start()
    def disable(self):
        self.enabled = 0
        self.stop()
    def is_enabled(self):
        return self.enabled
    def start(self):
        # Grab a handle to our event producer node.
        if not self.pnode_obj:
            try:
                self.pnode_obj = as_node(self.prodnode)
            except:
                mstr = 'Could not grab handle to our event producer node: %s' % self.prodnode
                self._logMsg(ERR, mstr)
                msglog.exception()

        if not self.pnode_subscribed:
            # Attempt to subscribe to events produced by
            # our event producer node.
            try:       
                self.pnode_obj.event_subscribe(self, self._event_class)
                self.pnode_subscribed = 1
            except:
                mstr = 'Could not subscribe to events from our Event Producer node (%s).' % self.prodnode
                self._logMsg(WARN, mstr)
                msglog.exception()
        #
        ConfigurableNode.start(self)
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

        variables = []
        self._subject = ''
        subject = self.subject
        while '$' in subject:
            index = subject.index('$')
            try:
                if subject[index+1] == '{':
                    end = string.find(subject,'}',index)
                    if end > -1:
                        var = subject[index:end+1]
                        variable = var[2:-1]
                        if '$' not in variable and '{' not in variable:
                            subject = string.replace(subject,var,'%s')
                            variables.append(variable)
            except IndexError:
                pass
            self._subject += subject[0:index+1]
            subject = subject[index+1:]
        self._subject += subject
        self._subject_vars = tuple(variables)
        
    def stop(self):
        ConfigurableNode.stop(self)
    ##
    # event handler
    def event_handler(self, event):
        if self.debug > 10:
            print event
        if event.__class__ == self._event_class:
            if self.debug > 0:
                msg = 'Got a new event: %s' % str(event)
                self._logMsg(INFO, msg)
            self.caught_event(event)
        else:
            msg = 'Got an unexpected event: %s.' % str(event)
            self._logMsg(ERR, msg)
    #
    def caught_event(self, event):
        self._trigger(time.time(),event)
    #
    def _trigger(self,timestamp,event):
        try:
            self._current_id = self._manager.unique_id()
            message = self._message
            for var in self._message_vars:
                if hasattr(event, var):
                    eattr = getattr(event, var)
                    message = string.replace(message,'%s',str(eattr),1)
                else:
                    message = string.replace(message,'%s','${%s}' % var, 1)
            subject = self._message
            for var in self._subject_vars:
                if hasattr(event, var):
                    eattr = getattr(event, var)
                    subject = string.replace(subject,'%s',str(eattr),1)
                else:
                    subject = string.replace(subject,'%s','${%s}' % var, 1)
            trigger = AlarmTriggerEvent(self,self._current_id,timestamp,
                                        event,{},message, subject)
            self.event_generate(trigger)
        except EInvalidValue:
            pass
    #
    # Note: caught, success and fail are part of the public interface exposed
    #       by alarm nodes which can be used by exporters to communicate status
    #       back about whether the alarm got delivered or not.
    def caught(self,alarm):
        pass
    #
    def success(self,alarm):
        pass
    #
    def fail(self,alarm):
        msglog.log('broadway',msglog.types.WARN,
                   'Failed sending alarm -> %s' % alarm)

##
# Major node browser hack!
class HTML:
    def __init__(self, text):
        self.__text = text
        return
    def __str__(self):
        return self.__text

def link_for_alarms():
    return "/nodebrowser/services/alarms/Device%20Unavailable%20Alarms/alarms"

def link_for_invoke(name, method, text):
    return ('<a href="%s/%s?action=invoke&method=%s'
            '&Content-Type=text/html">%s</a>' %
            (link_for_alarms(),
             urllib.quote_plus(name),
             urllib.quote_plus(method),
             urllib.quote_plus(text),)
            )

def state_and_return_link(alarm):
    return ('%s: Return to <a href="%s">%s</a>' %
            (alarm._state,
             link_for_alarms(),
             'Device Unavailable Alarms',)
            )

class DynamicComparisonTrigger(ComparisonTrigger):
    def start(self):
        ComparisonTrigger.start(self)
        self._manager.add_dynamic_alarm(self)
        return
    ##
    # Major node browser hack!
    def enable(self):
        ComparisonTrigger.enable(self)
        return HTML(state_and_return_link(self))
    def disable(self):
        ComparisonTrigger.disable(self)
        return HTML(state_and_return_link(self))
    def acknowledge(self):
        ComparisonTrigger.acknowledge(self)
        return HTML(state_and_return_link(self))
    def get(self, skipCache=0):
        state = self._state
        text = str(state)
        if state in (self.TRIGGERED, self.SENDING, self.SENT, self.ERROR):
            text += (
                ' (' +
                link_for_invoke(self.name, "acknowledge", "acknowledge") +
                ')'
                )
        if state in (self.DISABLED,):
            text += (
                ' (' +
                link_for_invoke(self.name, "enable", "enable") +
                ')'
                )
        else:
            text += (
                ' (' +
                link_for_invoke(self.name, "disable", "disable") +
                ')'
                )
        return HTML(text)
