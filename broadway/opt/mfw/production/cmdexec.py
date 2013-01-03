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
#=----------------------------------------------------------------------------
# cmdexec.py
#
# Execute a command, capture its output, and check for success/failure (0/1).
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

import os
from popen2 import Popen4

def execute_command(command):
    global test_logger

    sub_cmd = Popen4(command)
    cmd_output = sub_cmd.fromchild.readlines()
    status = sub_cmd.wait()

    if os.WIFEXITED(status):
        exit_status = os.WEXITSTATUS(status)
        if exit_status:
            return 0, cmd_output
    else:
        raise Exception('Test harness failure\nReason: %s.\n' %
            os.strerror(status))

    return 1, cmd_output

#=- EOF ----------------------------------------------------------------------