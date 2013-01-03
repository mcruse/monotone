"""
Copyright (C) 2002 2004 2010 2011 Cisco Systems

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
##
# This module provides a class to simplify the creation of 
# sgml based documents such as html and xml.  The class performs
# some simple error checking concerning tag balance and adds tabs and
# carriage returns to output where needed.
#
# @fixme Shouldn't we use something like Python's xml package with a
#        gernerator? 

import string

from mpx.lib.exceptions import EInvalidValue

class SGMLFormatter:
    def __init__(self):
        self.indent_depth = 0
        self.indent_string = ' '
        self.sgml_lines = []
        self.tags = []
    
    ##
    # Creates an sgml opening tag along with attributes
    # specified.
    #
    # @param tag  The name of the tag to open.
    # @param attributes  Dictionary of name/value pairs
    #                    to be added as parameters to the 
    #                    tag.
    # @optional
    #
    def open_tag(self, tag, **attributes):
        text = self.indent_depth * self.indent_string
        self.indent_depth += 1
        text += '<' + tag
        for attribute in attributes.keys():
            text += ' %s="%s"' % (attribute, attributes[attribute])
        text += '>'
        self.sgml_lines.append(text)
        self.tags.append(tag)
    def add_attribute(self, name, value):
        text = self.sgml_lines.pop()
        text = text[0:-1] + ' %s="%s">' % (name,value)
        self.sgml_lines.append(text)
    
    ##
    # Closes tag that was previously opened.
    #
    # @param tag  Tag that is to be closed.
    # @default None Will close tag that was last opened.
    # @throws EBadValue  If a tag is specified and it does
    #                    not match the last tag that was opened
    #                    then there is an error.
    #
    def close_tag(self, tag=None, same_line=0):
        last_tag = self.tags.pop()
        if tag == None:
            tag = last_tag
        elif tag != last_tag:
            raise EInvalidValue('tag', tag, 'tag %s is still open' % last_tag)
        self.indent_depth -= 1
        text = self.indent_depth * self.indent_string
        text += '</' + tag + '>'
        if same_line:
            text = self.sgml_lines.pop() + text.strip()
        self.sgml_lines.append(text)
        return
    ##
    # Open a tag with specified attributes and then close
    # it.  For use with tags that will have no text inserted 
    # between their open and close.
    #
    # @param tag  The name of the tag to be opened.
    # @param attributes  The attributes to be placed in 
    #                    the opening tag.
    #
    def open_close_tag(self, tag, **attributes):
        text = self.indent_depth * self.indent_string
        text += '<' + tag
        for attribute in attributes.keys():
            text += ' %s="%s"' % (attribute, attributes[attribute])
        text += '/>'
        self.sgml_lines.append(text)
    ##
    # Open a tag with specified attributes and then close
    # it providing control over the exact order the attributes are listed.
    # For use with tags that will have no text inserted 
    # between their open and close.
    #
    # @param tag  The name of the tag to be opened.
    # @param attribute_pairs  A list of (name,value) lists.
    #
    def open_close_tag_ex(self, tag, attribute_pairs):
        text = self.indent_depth * self.indent_string
        text += '<' + tag
        for pair in attribute_pairs:
            attribute = pair[0]
            value = pair[1]
            text += ' %s="%s"' % (attribute, value)
        text += '/>'
        self.sgml_lines.append(text)
    ##
    # Insert a tag that has no closing tag
    # associated with it.
    #
    # @param tag  The tag to be inserted.
    #
    def single_tag(self, tag):
        text = self.sgml_lines.pop()
        text += '<' + tag + '>'
        self.sgml_lines.append(text)
    
    ##
    # Add text to current at current document location.
    #
    # @param text  The text to be added.
    #
    def add_text(self, text):
        if len(self.sgml_lines) > 0:
            text = self.sgml_lines.pop() + text
        self.sgml_lines.append(text)
    
    ##
    # Output sgml that has been built.
    #
    # @return String containing sgml formed.
    # @note All open tags will automatically be closed.
    #
    def output_complete(self, pretty=1):
        while self.tags:
            self.close_tag()
        return self.output(pretty)
    
    def output(self, pretty=1):
        if pretty:
            output = string.join(self.sgml_lines, '\n')
        else:
            output = ''
            for line in self.sgml_lines:
                output += line.strip()
        if self.sgml_lines:
            self.sgml_lines = ['']
        return output


