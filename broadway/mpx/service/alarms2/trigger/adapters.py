"""
Copyright (C) 2010 2011 Cisco Systems

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
from mpx.lib.node import as_node
from mpx.lib.neode.node import ConfigurableNode
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry.interfaces import IPickles
from interfaces import ITrigger

class TriggerPickler(object):
    implements(IPickles)
    adapts(ITrigger)

    def __init__(self, trigger):
        self.trigger = trigger
    def __getstate__(self):
        trigger = self.trigger
        if not hasattr(trigger, '__picklestate'):
            state = {'class': type(trigger),
                     'url': trigger.url,
                     'config': trigger.configuration()}
            trigger.__picklestate = state
        state = trigger.__picklestate
        state['targets'] = []
        targets = trigger.get_targets(True)
        for target in targets:
            if not isinstance(target, str):
                target = target.url
            state['targets'].append(target)
        state['running'] = trigger.is_running()
        return state
    def __setstate__(self, state):
        self.trigger = None
        self.state = state
    def __call__(self):
        if self.trigger is None:
            try: self.trigger = as_node(self.state['url'])
            except KeyError: self.trigger = self.state.get('class')()
            config = self.state['config']
            parent = as_node(config['parent'])
            config.setdefault('nodespace', parent.nodespace)
            self.trigger.configure(config)
            if self.state['running']:
                self.trigger.start()
        for target in self.state.get('targets', []):
            self.trigger.add_target(target)
        return self.trigger

register_adapter(TriggerPickler)
