"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import time
from StringIO import StringIO
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_onoff
from mpx.lib.configure import as_boolean
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.persistent import PersistentDataObject
from mpx.service.data import Transporter
from mpx.lib import ftplib

##
# Generic FTP transporter.  Takes data and
# sends it over network via FTP.
class FTPTransporter(Transporter):
    _last = None
    ##
    # Configure object.
    #
    # @key url  The url that data is to be sent
    #           to.  For example: ftp.hostname.com/tmp/.
    # @key username  The username for the FTP session.
    # @key password  The password for the FTP session.
    # @key file_prefix  The prefix for files that are
    #                   created when data is uploaded.
    # @key file_suffix The suffix to be appended to all
    #                  files created when data is uploaded.
    # @default .dat
    # @key name_scheme  Naming scheme to be used for created
    #                   each file.
    # @value timestamp  Insert timestamp between file_prefix
    #                   and file_suffix for each upload.
    # @value count  Insert incrmemental count of uploads between
    #               prefix and suffix.
    # @value none  Do not use a naming scheme.  Each upload
    #              will overwrite the previous upload.
    # @default timestamp.
    #
    def configure(self, config):
        set_attribute(self, 'host', REQUIRED, config)
        set_attribute(self, 'port', 21, config, int)
        set_attribute(self, 'directory', '', config)
        set_attribute(self, 'username', REQUIRED, config)
        set_attribute(self, 'password', REQUIRED, config)
        #CSCtn64870
        if (config.has_key('timeout') and config['timeout'] == ''):
            config['timeout'] = 'None'
        set_attribute(self, 'timeout', None, config, float)
        set_attribute(self, 'file_prefix', 'cisco', config)
        set_attribute(self, 'file_suffix', '.dat', config)
        set_attribute(self, 'name_scheme', 'timestamp', config)
        set_attribute(self, 'timestamp_format', '%s', config)
        set_attribute(self, 'passive_mode', 1, config, as_boolean)
        set_attribute(self, 'file_append', 0, config, as_boolean)
        Transporter.configure(self, config)
        if self._last is None:
            self._last = PersistentDataObject(self)
            self._last.filename = None
            self._last.count = 1
            self._last.load()
    def configuration(self):
        config = Transporter.configuration(self)
        get_attribute(self, 'host', config)
        get_attribute(self, 'port', config, str)
        get_attribute(self, 'directory', config)
        get_attribute(self, 'username', config)
        get_attribute(self, 'password', config)
        get_attribute(self, 'timeout', config, str)
        get_attribute(self, 'file_prefix', config)
        get_attribute(self, 'file_suffix', config)
        get_attribute(self, 'name_scheme', config)
        get_attribute(self, 'timestamp_format', config)
        get_attribute(self, 'passive_mode', config, as_onoff)
        get_attribute(self, 'file_append', config, str)
        return config
    def transport(self, data):
        filename = self._generate_filename()
        if type(data) == type(''):
            data = StringIO(data)
        ftp = ftplib.FTP()
        ftp.connect(self.host, self.port, self.timeout)
        finished = 0
        try:
            ftp.login(self.username, self.password)
            ftp.set_pasv(self.passive_mode != 0)
            if self.file_append and not self.name_scheme:
                ftp.storlines('APPE ' + self._full_file_name(filename), data)
            else:
                ftp.storlines('STOR ' + self._full_file_name(filename), data)
            self._last.save()
            finished = 1
            data.close()
        finally:
            if not finished:
                # quit hangs is exception.
                ftp.close()
            else:
                try:
                    ftp.quit()
                except:
                    ftp.close()
    def _generate_filename(self):
        append = ''
        filename = self.file_prefix
        if self.name_scheme == 'incremental':
            append = '%s' % self._last.count
        elif self.name_scheme == 'timestamp':
            filetime = self.parent.time_function(self.parent.scheduled_time())
            filename += time.strftime(self.timestamp_format, filetime)
            append = '_%s' % (self._last.count + 1)
            if filename != self._last.filename:
                self._last.count = 0
                append = ''
        self._last.count += 1
        self._last.filename = filename
        return filename + append + self.file_suffix
    def _full_file_name(self, filename):
        if self.directory:
            if self.directory[-1:] == '/':
                filename =  self.directory + filename
            else:
                filename = self.directory + '/' + filename
        return filename


def factory():
    return FTPTransporter()
