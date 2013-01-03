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
from mpx.componentry import Interface

class IFormatter(Interface):
    """
        Generic formatter interface.  Instances should 
        provide one of the more specialized versions.
    """
    def format(data, **kw):
        """
            Format data 'data' and return stream object which implements 
            read and readline methods at a minimum.
        """

class ILogDataFormatter(IFormatter):
    """
        Specialized formatter for handling log data.
    """
    def format(logdata, **kw):
        """
            See IFormatter.format method for general documentation.
            Parameter 'logdata' must be a tuple of dictionaries where 
            each dictionary maps node names to node values.
        """

class ICOVDataFormatter(IFormatter):
    """
    """
    def format(covdata, **kw):
        """
            See IFormatter.format method for general documentation.
            Parameter 'covdata' must be result dictionary such as 
            that returned by subscription manager's poll_changed.  This 
            dictionary maps node IDs to Result dictionaries.  Result 
            dictionaries have keys: 'value', 'timestamp', and 'cached.'
            The value associated with 'value' is the point's current value.
        """
