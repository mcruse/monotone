"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
import os
import time
import StringIO
from mpx.service.data import Transporter
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute

class WritingTransporter(Transporter):
    def configure(self, config):
        set_attribute(self, 'directory', '/tmp', config)
        set_attribute(self, 'file_prefix', REQUIRED, config)
        set_attribute(self, 'file_suffix', REQUIRED, config)
        set_attribute(self, 'name_scheme', None, config)
        set_attribute(self, 'timestamp_format', '%s', config)
        Transporter.configure(self, config)
        self._last = PersistentDataObject(self)
        self._last.filename = None
        self._last.count = 1
        self._last.load()
    def configuration(self):
        config = Transporter.configuration(self)
        get_attribute(self, 'directory', config)
        get_attribute(self, 'file_prefix', config)
        get_attribute(self, 'file_suffix', config)
        get_attribute(self, 'name_scheme', config)
        get_attribute(self, 'timestamp_format', config)
        return config
    def transport(self, data):
        if type(data) == type(''):
            data = StringIO.StringIO(data)
        filename = self._generate_filename()
        tempname = filename + '.tmp'
        file = open(tempname,'w')
        try:
            write = data.read(1024)
            while write:
                file.write(write)
                write = data.read(1024)
        finally:
            file.close()
        os.chmod(tempname,0444)
        os.rename(tempname,filename)
    def _generate_filename(self):
        filename = self.file_prefix
        append = ''
        if self.name_scheme == 'incremental':
            append = '%s' % self._last.count
        elif self.name_scheme == 'timestamp':
            file_time = self.parent.time_function(self.parent.scheduled_time())
            filename = filename + time.strftime(self.timestamp_format,file_time)
            append = '_%s' % (self._last.count + 1)
            if filename != self._last.filename:
                self._last.count = 0
                append = ''
        self._last.count += 1
        self._last.filename = filename
        return os.path.join(self.directory,filename + append + self.file_suffix)
