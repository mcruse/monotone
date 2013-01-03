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
from mpx.lib.node import ConfigurableNode
from mpx.lib.configure import set_attribute,get_attribute

"""
Instructions For Usage: 
(0) The name of the key that represents the HTML tags for "Download File" link MUST have the
    prefix "HTML_". Eg, the attribute key "HTML_target_file" should have the link HTML tags as a value.
    See the code below for an example.
(1) Build project. 
(2) Install envenergy.mpx on target Mediator (or PC).
(3) Modify target broadway.xml file by adding these lines under /interfaces/com1:
    <node name='test_html' node_id='999999999' module='mpx.lib.node.test_html.TestHtmlNode'  config_builder=''  inherant='true' description='Test node for HTML tags as node attrs'>
    </node>
(4) Copy the file mpx/lib/node/test_html_node.xyz to the HTTP server root directory (usually /var/mpx/www/http/).
(5) Start MFW.
(6) Open Browser (eg Mozilla). Verify that the Browser does NOT support inherent processing
    of files with extension ".xyz". (Else, no save dialog will appear when the Download File
    link is clicked...)
(7) Navigate to /interfaces/com1/test_html.
(8) Verify that the configuration value of key "HTML_target_file" is the link named "Download File".
"""


class TestHtmlNode(ConfigurableNode):
    def __init__(self):
        ConfigurableNode.__init__(self)
        return
    def configure(self, cd):
        ConfigurableNode.configure(self,cd)
        set_attribute(self,'www_file_path','/test_html_node.xyz',cd,str)
        html_str = '<a href=%s>Download File</a>' % self.www_file_path
        set_attribute(self,'HTML_target_file',html_str,cd,str)
        return
    def configuration(self):
        cd = ConfigurableNode.configuration(self)
        get_attribute(self,'www_file_path',cd,str)
        get_attribute(self,'HTML_target_file',cd,str)
        return cd
    
