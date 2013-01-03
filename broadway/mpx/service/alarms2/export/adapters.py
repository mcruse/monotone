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
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.neode.node import ConfigurableNode
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry.interfaces import IPickles
from interfaces import IAlarmExporter

class ExporterPickler(object):
    implements(IPickles)
    adapts(IAlarmExporter)

    def __init__(self, exporter):
        self.exporter = exporter
    def __getstate__(self):
        exporter = self.exporter
        if not hasattr(exporter, '__picklestate'):
            state = {'class': type(exporter),
                     'url': exporter.url,
                     'config': exporter.configuration()}
            exporter.__picklestate = state
        state = exporter.__picklestate
        sources = self.exporter.get_sources()
        state['sources'] = {}
        for source in sources:
            state['sources'][source.url] = self.exporter.get_event_names(source)
        return state
    def __setstate__(self, state):
        self.exporter = None
        self.state = state
    def __call__(self):
        if self.exporter is None:
            try: self.exporter = as_node(self.state['url'])
            except KeyError: self.exporter = self.state.get('class')()
            config = self.state['config']
            parent = as_node(config['parent'])
            config.setdefault('nodespace', parent.nodespace)
            self.exporter.configure(config)
            self.exporter.start()
        for source, args in self.state.get('sources', {}).items():
            try:
                self.exporter.add_source(source, *args)
            except:
                msglog.exception()
        return self.exporter
register_adapter(ExporterPickler)
