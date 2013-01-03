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
import cgi
import urllib
import itertools
from HTMLgen import Formtools
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.service.cloud.interfaces import ICloudManager
from mpx.lib.htmlgen import *

addform = """
<form action="/cloudconfig" method="post" id="cloud-config">
    host:
    <input type="text" name="add" maxlength="255"/>
    <input type="submit" value="commit" name="SubmitButton" style="display: none;"/>
 </form>   
"""
addform = urllib.quote(addform)

class HTMLCloudManager(object):
    implements(IWebContent)
    adapts(ICloudManager)
    def __init__(self, manager):
        self.manager = manager
        self.base_doc = HTMLgen.SimpleDocument(title='Cloud Host Editor')
    def render(self):
        attrs = KeyWordAssist()
        request_path = '/cloudconfig'
        document = self.base_doc.copy()

        formation_section = HTMLgen.Div(**attrs('class', 'section'))
        formation_table = HTMLgen.TableLite(
            id="cloud-config", **attrs('class', 'configuration-table'))
        formation_header = HTMLgen.TR(**attrs('class','table-header'))
        for header in ['Host', 'Action']:
            headcell = HTMLgen.TH(header, scope="col", abbr=header,
                                  id="%sheader" % header)
            if header == "Action":
                setattr(headcell, "class", "control")
            formation_header.append(headcell)
        formation_table.append(formation_header)

        formation=self.manager.nformation.get_formation()
        classes = itertools.cycle(['light', 'dark'])
        for peer in formation:
            row = HTMLgen.TR(**attrs('class', classes.next()))
            row.append(HTMLgen.TH(peer))
            actioncell = HTMLgen.TD(**attrs('class', 'control'))
            encoded = cgi.escape(peer)
            actions = ['remove']
            for action in actions:
                # Don't allow removal of this peer.                
                if peer == self.manager.peer: continue
                formId = encoded
                actionform = HTMLgen.Form(request_path)
                actioninput = HTMLgen.Input(name=action, 
                                            value=encoded, type='hidden')
                actionform.append(actioninput)
                if action == "remove":
                    actionform.name = "Remove Host"
                    actionform = adorn(actionform, targetID="cloud-config", id=formId)
                actionform.submit.value = ' - '
                actionform.submit.onClick = ("return confirmDialog('" + formId + "', 'Remove"
                                             " peer from cloud?', false);")
                actioncell.append(actionform)
                if len(actions) > 1 and action != actions[-1]: 
                    actioncell.append(' ')
            row.append(actioncell)
            formation_table.append(row)
        formation_section.append(formation_table)
        
        add_form = HTMLgen.Form(request_path)
       #addinput = HTMLgen.Input(name='add', value='', type='text')
       #add_form.append(addinput)
       #add_form = adorn(add_form, targetID="cloud-config")
        add_form.submit.value = ' + '
        add_form.submit.name = "Add Host"
        add_form.submit.onClick = "return popup_form(this, '%s', true)" % addform
        formation_section.append(add_form)
        document.append(formation_section)
        return str(document)

register_adapter(HTMLCloudManager)

