"""
Copyright (C) 2008 2011 Cisco Systems

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
import weakref
import paramiko
import paramiko.logging22
from StringIO import StringIO
from mpx.lib import msglog
from mpx.service.data.ftptransport import FTPTransporter
DEBUG = False


class SFTPTransporter(FTPTransporter):
    def __init__(self, *args, **kw):
        self.previous_transport = None
        super(SFTPTransporter, self).__init__(*args, **kw)
        self.port = 22
    def transport(self, data):
        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username=self.username, password=self.password)
        try:
            self._ftpdata(transport, data)
        finally:
            transport.close()
    def transport(self, data):
        transport = self._setuptransport()
        try:
            self._transportdata(transport, data)
        finally:
            transport.close()            
    def _transportdata(self, transport, data):
        sftp = self._setupsftp(transport)
        try:
            self._tansferdata(sftp, data)
        finally:
            sftp.close()
    def _tansferdata(self, sftp, data):
        if isinstance(data, str):
            data = StringIO(data)
        file = self._setupfile(sftp)
        try:
            bytes = data.read(32768)
            while bytes:
                file.write(bytes)
                bytes = data.read(32768)
        finally:
            data.close()
            file.close()
    def _setuptransport(self):
        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username=self.username, password=self.password)
        return transport
    def _setupsftp(self, transport):
        sftp = paramiko.SFTPClient.from_transport(transport)
        if self.timeout:
            sftp.sock.settimeout(self.timeout)
        return sftp        
    def _setupfile(self, sftp):
        if self.file_append and not self.name_scheme:
            filemode = 'a'
        else:
            filemode = 'w'
        filename = self._generate_filename()
        filename = self._full_file_name(filename)
        return sftp.open(filename, filemode)


class LoggingWrapper(object):
    def __init__(self, logging):
        self.logging = logging
    def __getattr__(self, name):
        return getattr(self.logging, name)
    def getLogger(self, name):
        return MessageLogger(name)


class MessageLogger(paramiko.logging22.logger):
    levelmap = {paramiko.common.DEBUG: msglog.types.DB,
                paramiko.common.INFO: msglog.types.INFO,
                paramiko.common.WARNING: msglog.types.WARN,
                paramiko.common.ERROR: msglog.types.ERR,
                paramiko.common.CRITICAL: msglog.types.ERR}
    def __init__(self, name):
        self.name = name
        super(MessageLogger, self).__init__()
    def log(self, level, message, *args):
        if args:
            try:
                message = message % args
            except:
                argstring = ', '.join([str(arg) for arg in args])
                message = message + '(extra: %s)' % argstring
        if not isinstance(level, str):
            level = self.levelmap[level]
        if DEBUG or (level != msglog.types.DB and level != msglog.types.INFO):
            # Unfortunately Paramiko defines informational logging 
            # differently than we do, outputting what we would 
            # consider debugging messages as informational ones.
            msglog.log(self.name, level, message)


paramiko.common.logging = LoggingWrapper(paramiko.common.logging)
paramiko.util.logging = paramiko.common.logging
