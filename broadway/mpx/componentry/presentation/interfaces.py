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

class ITemplate(Interface):
    """
        Object accepts IStorageField object and 
        applies formatting specified by template 
        file, such as HTML source file.
        
        Object constructor takes string argument 
        that may be: path to template content file, 
        or a string containing the template data itself.
        
        The constructor checks to see if the argument 
        specifies a path of an existing file.  If so, it 
        reads the contents of the specified file and uses 
        that as the template source; if not it uses the 
        parameter directly as the template.
        
        Optional argument specifying that argument is meant 
        to be a file path, and therefore an exception should 
        be raised if file does not exist.
        
        Templates take strings containing identifiers delimited 
        by '$identifier' or ${identifier}.  Both delimiters 
        have essentially the same meaning, however the second 
        identifier can be used in places where identifier is 
        otherwise interpolated into non-delimited string.  For example:
            
            - "Hello $name, how are you?", or
            -  "It is a nice ${prefix}day." 
        
        Use "$$" to include literal $ in template output text.
        
        See string.Template for additional documentation.
    """
    
    template = Attribute("""Data being used as template data""")
    
    def substitute(mapping, **kws):
        """
            Performs the template substitution, returning a new string. 
            'mapping' is any dictionary-like object with keys that match 
            the placeholders in the template. 
            
            Alternatively, you can provide keyword arguments, where the 
            keywords are the placeholders. 
            
            When both mapping and kws are given and there are duplicates, 
            the placeholders from kws take precedence.
        """
    def safe_substitute(mapping, **kws):
        """
            Like substitute(), except that if placeholders are missing from 
            mapping and kws, instead of raising a KeyError exception, the 
            original placeholder will appear in the resulting string intact. 
            
            Also, unlike with substitute(), any other appearances of the "$" 
            will simply return "$" instead of raising ValueError.
            
            While other exceptions may still occur, this method is called 
            ``safe'' because substitutions always tries to return a usable 
            string instead of raising an exception. In another sense, 
            safe_substitute() may be anything other than safe, since it 
            will silently ignore malformed templates containing dangling 
            delimiters, unmatched braces, or placeholders that are not 
            valid Python identifiers.
        """
 