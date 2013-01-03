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
from clu import CommandLineUtility

class MPX_Diag(CommandLineUtility):
    HELP = """
mpx_diag:  Command-line utility that returns assorted
           information about a mediator.
"""
    OVERVIEW = """
"""
    def __init__(self):
        CommandLineUtility.__init__(self, self.HELP)
        self.register_command("properties", self.properties,
                              "Display the properties for the current " +
                              "environment.",
                              ["props"])
        return
    def properties(self, command):
        import mpx
        self.stdout.write(repr(mpx.properties))
        return
    def run_command(self, command):
        self.stdout.write(self.HELP)
        self.stdout.write(self.OVERVIEW)
        self.stdout.write("\n")
        self.stdout.write("sub-commands:\n\n")
        keys = self.commands().keys()
        keys.sort()
        for key in keys:
            info = self.commands()[key].help_description()
            self.stdout.write("  %s" % info['name'])
            for alias in info['aliases']:
                self.stdout.write(", %s" % alias)
            self.stdout.write(":\n")
            self.stdout.write("    %s" % info['text'])
            self.stdout.write("\n")
        return 0
if __name__ == '__main__':
    main = MPX_Diag()
    raise SystemExit(main.run())
