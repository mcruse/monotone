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
import sys
from code import InteractiveConsole
PS1 = getattr(sys, "ps1", ">>> ")
PS2 = getattr(sys, "ps2", "... ")

class InteractiveSession(InteractiveConsole):
    def __init__(self, channel):
        self.channel = channel
        InteractiveConsole.__init__(self, self.channel.namespace)
    def start(self):
        if not sys.stdout.attached(self):
            sys.stdout.attach(self)
        if not sys.stderr.attached(self):
            sys.stderr.attach(self)
    def stop(self):
        if sys.stdout.attached(self):
            sys.stdout.detach(self)
        if sys.stderr.attached(self):
            sys.stderr.detach(self)
    def prompt(self, banner=""):
        self.write(banner)
        self.prompt_next()
    def handle(self, line):
        result = InteractiveConsole.push(self, line)
        if result:
            self.prompt_more()
        else:
            self.prompt_next()
        return result
    def write(self, bytes):
        self.channel.push(bytes)
    def prompt_next(self):
        self.write(PS1)
    def prompt_more(self):
        self.write(PS2)
