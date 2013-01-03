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
from mpx.componentry import Interface, Attribute
# Define IWebContent, ISimpleElement, IContainerElement, IDocumentElement

class IWebContent(Interface):
    """
        Content that can be rendered between 
        HTML tags.  Contains no elements.
    """
    def render():
        """
            Return simple string of data
            to be placed into document flow.
        """

class ISimpleElement(IWebContent):
    """
        An HTML element that can contain 
        attributes and content.
    """
    def set_content(data):
        """
            Sets string object holding element's content.
        """
    def set_attribute(name, value):
        """
            Set element attribute.
        """
    def get_attribute(name):
        """
            Return element attribute specified by name.
        """
    def get_attributes():
        """
            Return name: value dictionary of all element attributes.
        """
    def get_attribute_names():
        """
            Return list of all attribute names.
        """
    def get_content():
        """
            Return elements conten object.
        """
    def render():
        """
            Render open tag with attributes, content, and close tag.
        """

class IContainerElement(ISimpleElement):
    """
        An HTML element that can contain content, 
        other contanier elements, and other elements.
    """
    def add_element(element):
        """
            Add element as child.
        """

class IDocumentElement(IContainerElement):
    """
        Top level HTML page.  This object's render 
        can be returned directly to browser.
    """
