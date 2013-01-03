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
# CAUTION: EXAMPLE CODE ONLY!
# This file could be the starting point for a unit test for the flash module,
# or a command-line version of labman.  It needs some work, however.
import flash

def print_progress(flash, step, of):
    print "%d of %d" % (step, of)

def print_messages(flash, message):
    print message

x = flash.Flash('/dev/hda', '/mnt', print_progress, print_messages)
x.make_partition()
x.make_filesystem()
x.mount()
x.extract_moe('/home/moe/moe-2.0.0rc58.tgz')
x.make_bootrecord()
x.extract_packages('','')
x.umount()
