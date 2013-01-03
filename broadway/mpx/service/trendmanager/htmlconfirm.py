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
import urllib
from HTMLgen import HTMLgen

from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter

from mpx.www.w3c.xhtml.interfaces import IWebContent

from trendutil import CustomButton
from trendutil import CustomForm
from trendutil import CustomInput
from trendutil import CustomLabel

from interfaces import IConfirmUpdateTrend

class HTMLConfirmUpdateTrend(object):
    implements(IWebContent)
    adapts(IConfirmUpdateTrend)
    def __init__(self, confirmupdate):
        ##
        # Trend we are adapting.
        self.confirmupdate = confirmupdate
        ##
        # Currently only support confirming changes to point definitions,
        # passes on changes to the period.
        assert confirmupdate.change_points
        assert not confirmupdate.change_name
        assert not confirmupdate.change_preferences
        #
        self.confirm_form = None
        self.hidden_point_div = None
        self.point_confirmation_div = None
        return
    def create_hidden_point_div(self):
        hidden_point_div = HTMLgen.Div(**{'class':'hiddenformdata'})
        new_points = self.confirmupdate.new_points
        for point_index in xrange(0,9):
            point_position = point_index+1
            point_name_value = ""
            point_node_value = ""
            if len(new_points) > point_index:
                point_cfg = new_points[point_position-1]
                point_name_value = point_cfg['name']
                point_node_value = point_cfg['node']
            point_name_id = "point%d" % point_position
            name_input = CustomInput(**{
                'type':'hidden',
                'value':point_name_value,
                'name':point_name_id,
                'id':point_name_id,
                })
            hidden_point_div.append(name_input)
            point_node_id = "node%d" % point_position
            node_input = CustomInput(**{
                'type':'hidden',
                'value':point_node_value,
                'name':point_node_id,
                'id':point_node_id,
                })
            hidden_point_div.append(node_input)
        hidden_point_div.append(CustomInput(
            **{"type":"hidden","id":"period", "name":"period",
               "value":self.confirmupdate.new_period}))
        return hidden_point_div
    def create_point_confirmation(self):
        point_confirmation_div = HTMLgen.Div(**{'class':'confirmationdiv'})
        delete_control = HTMLgen.Select((("Delete existing data","1"),
                                         ("Save existing data","0")),
                                        **{"name":"deletedata",
                                           "size":1,
                                           "selected":("1",),})
        confirmation_text = HTMLgen.Text(
            "Warning:  Changing the name or value of a previously"
            " defined trend point my lead to unexpected results"
            " with existing data.  It is highly recommended that"
            " you delete the existing trend data: "
            )
        if self.confirmupdate.delete_level > 1:
            confirmation_text = HTMLgen.Text(
                "Warning:  Adding points to an existing trend requires"
                " deleting existing trend data.  Confirming changes"
                " will delete the existing trend data."
                )
            delete_control = CustomInput(**{
                'type':'hidden',
                'value':"1",
                'name':'deletedata',
                })
        point_confirmation_div.append(
            confirmation_text,
            delete_control
            )
        return point_confirmation_div
    def create_confirm_form(self):
        confirm_form = CustomForm('/trendmanager')
        confirm_form.submit = HTMLgen.Span(**{"class":"savespan"})
        confirm_form.submit.append(
            CustomInput(type='hidden', name='trend',
                        value=self.confirmupdate.encoded_name)
            )
        confirm_form.submit.append(
            CustomInput(type='submit', name='confirmupdate', value='Commit')
            )
        confirm_form.submit.append(
            CustomInput(type='submit', name='cancelupdate', value='Cancel')
            )
        return confirm_form
    def render(self):
        document = HTMLgen.SimpleDocument(
            title="Confirm",
            stylesheet='/omega/trendmanager/styles.css',
            )
        # Hack-around to set the class on the BODY for HTMLGen
        document.append(
            HTMLgen.Script(code="""
              document.body.className = 'manager';
              """),
            )
        document.append(
            HTMLgen.Heading(2, "Trend Confirm Changes",
                                           id="editorlabel")
            )
        section = HTMLgen.Div(**{'class':'section'})
        self.confirm_form = self.create_confirm_form()
        self.hidden_point_div = self.create_hidden_point_div()
        self.confirm_form.append(self.hidden_point_div)
        self.point_confirmation_div = self.create_point_confirmation()
        self.confirm_form.append(self.point_confirmation_div)
        section.append(self.confirm_form)
        document.append(section)
        return str(document)
register_adapter(HTMLConfirmUpdateTrend)
