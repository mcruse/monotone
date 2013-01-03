"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
import _builtin_rexec

##
# The Broadway specific version of the Python's rexec.RExec class used to
# provide a 'safe' environment for evaluating arbitrary code fragments.
#
# @todo Customize this class to provide a sensible default environment
#       specifically for Broadway.
# 
# @see http://www.python.org/doc/current/lib/module-rexec.html
# @todo Ensure that rexec.RExec is thread safe.  If it is not, make this
#       class thread safe.  A better policy might be that callers must be
#       thread safe, that way there is less overhead.
class RExec(_builtin_rexec.RExec):
  ##
  # Create or replace the <code>name</code> in the restricted environment's
  # global namespace to refer to <code>value</code>.
  def update_global_name(self, name, value):
    self.update_global_names({name:value})
  ##
  # Create or replace the names in the restricted environment's global
  # namespace with the pased <code>dict</code>ionary.
  def update_global_names(self, dict):
    self.add_module('__main__').__dict__.update(dict)

del _builtin_rexec
