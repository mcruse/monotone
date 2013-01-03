"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
from feed import rss
from feed import tools
from mpx.www.w3c.syndication.rss2.interfaces import IRSS2ItemElement
from mpx.componentry import register_adapter
from mpx.componentry import implements
from mpx.componentry import adapts
from interfaces import IFaultEvent

class RSS2FaultEventItem(object):
    implements(IRSS2ItemElement)
    adapts(IFaultEvent)
    
    def __init__(self, faultevent):
        self.faultevent = faultevent
    def as_item(self):
        event = self.faultevent
        item = rss.Item()
        title = event.title
        faulttype = event.faulttype
        #item.title = rss.Title('%s: %s' % (title, faulttype))
        item.title = rss.Title(
            '%s (%s): %s' % (title, 'P1', event.state.upper()))
        item.link = rss.Link(
            'http://%s/syndication?guid=%s' % (event.origin, event.GUID))
        item.pub_date = rss.PubDate(event.timestamp)
        description = event.description
        event_history = event.history + [event.current_event]
        for change in event_history:
            description += '<br />\n%s.  ' % change.detail
        item.description = rss.Description(tools.escape_html(description))
        item.guid = rss.Guid(event.GUID)
        item.source = rss.Source(
            event.LOCALORIGIN, 'http://%s/syndication' % event.LOCALORIGIN)
        for category in event.types:
            item.categories.append(rss.Category(category))
        return item
    def render(self):
        return str(self.as_item())

register_adapter(RSS2FaultEventItem)
