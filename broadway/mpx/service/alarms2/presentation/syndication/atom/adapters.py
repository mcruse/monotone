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
import time
import urllib
from os import path
from feed import atom
from mpx.componentry import adapts
from mpx.componentry import implements
from mpx.componentry import register_adapter
from mpx.service.alarms2.interfaces import IAlarmManager
from mpx.service.alarms2.interfaces import IFlatAlarmManager
from mpx.www.w3c.syndication.atom.interfaces import IAtomDocument

class AtomSyndicator(object):
    implements(IAtomDocument)
    adapts(IAlarmManager)
    xml_declaration = '<?xml version="1.0" encoding="utf-8"?>'

    def __init__(self, manager):
        self.manager = manager
        self.flattened = IFlatAlarmManager(manager)        
        self.uri_base = self.manager.nodespace.url
        self.manager_url = urllib.quote(self.manager.url)
        self.feed_id = self.uri_base + self.manager_url
        self.link_base = self.uri_base + '/syndication' + self.manager_url
        self.categories = {
            'raised': atom.Category("Raised"),
            'inactive': atom.Category("Inactive"),
            'accepted': atom.Category("Accepted"),
            'cleared': atom.Category("Cleared"),
            'closed': atom.Category("Closed")
        }
        super(AtomSyndicator, self).__init__(manager)

    def render(self, request_path = None, cache_id = None):
        return str(self.get(request_path, cache_id))

    def get(self, request_path, cache_id):
        output = self.xml_declaration + '\n'
        xmldoc = self.setup_xmldoc(request_path)
        feed = xmldoc.root_element
        entries = self.setup_entries(request_path, cache_id)
        map(feed.entries.append, entries)
        return xmldoc

    def setup_xmldoc(self, request_path):
        xmldoc = atom.XMLDoc()
        feed = atom.Feed()
        feed.title = atom.Title(self.manager.name)
        feed.id = atom.Id(self.feed_id)
        xmldoc.root_element = feed
        return xmldoc

    def setup_entries(self, request_path, cache_id):
        entries = []
        content = "Alarm %s switched to %s state at %s.\n\n"
        content += "Please visit the Alarm Management link provided "
        content += "in this entry to view details and make modifications."
        t_update = time.time()
        updated = atom.Updated(t_update)
        for event in self.flattened:
            if event.state == 'inactive':
                continue
            entry = atom.Entry()
            entry.title = atom.Title(event.name)
            entry.id = atom.Id(event.id)
            entry.summary = atom.Summary('Alarm %s' % event.state)
            entry.published = atom.Published(event.timestamp)
            entry.updated = updated
            entry_content = content % (event.name, event.state.upper(),
                                       entry.published.text)
            entry.content = atom.Content(entry_content)
            entry.categories.insert(0, self.categories[event.state])
            entry.link = atom.Link(
                path.join(self.link_base, urllib.quote(event.name), event.id))
            entries.append(entry)
        return entries

register_adapter(AtomSyndicator)
