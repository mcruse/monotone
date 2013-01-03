"""
Copyright (C) 2002 2003 2009 2011 Cisco Systems

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
from M2Crypto import Rand, SSL
from mpx.service import ServiceNode
from mpx.service.network import http
from mpx.service.network.https._https import HTTPSServer
from mpx.lib.configure import set_attribute, get_attribute, \
     REQUIRED
from mpx.lib.persistent import PersistentDataObject
from mpx.lib import certificate
from mpx import properties
from tools import makecert
from mpx.lib import msglog

class Server(http.Server):
    # Override http.Server's class references.
    server_class = HTTPSServer
    server_type = 'HTTPS'
    def configure(self, config):
        http.Server.configure(self, config)
        set_attribute(self, 'server_cert',
                      '${mpx.properties.CERTIFICATE_PEM_FILE}',
                      config)
        set_attribute(self, 'key_file',
                      '${mpx.properties.PRIVATE_KEY_FILE}',
                      config)
        set_attribute(self, 'country', REQUIRED, config)
        set_attribute(self, 'state', REQUIRED, config)
        set_attribute(self, 'city', REQUIRED, config)
        set_attribute(self, 'organization', REQUIRED, config)
        set_attribute(self, 'organizational_unit', REQUIRED, config)
        set_attribute(self, 'common_name', REQUIRED, config)
        if self.common_name == 'auto':
            domainname = certificate.get_domain()
            self.common_name = certificate.get_host()
            if domainname:
                self.common_name += "." + domainname
        set_attribute(self, 'email', REQUIRED, config)
        return
    def configuration(self):
        config = http.Server.configuration(self)
        get_attribute(self, 'server_cert', config)
        get_attribute(self, 'key_file', config)
        get_attribute(self, 'country', config)
        get_attribute(self, 'state', config)
        get_attribute(self, 'city', config)
        get_attribute(self, 'organization', config)
        get_attribute(self, 'organizational_unit', config)
        get_attribute(self, 'common_name', config)
        get_attribute(self, 'email', config)                    
        return config
    
    def _setup_server(self):
        self._certificate_maintenance()
        ssl_ctx=SSL.Context('sslv23')
        ssl_ctx.load_cert(self.server_cert, self.key_file)
        ssl_ctx.set_allow_unknown_ca(1)
        # @fixme Really hard-code '127.0.0.1'?
        ssl_ctx.set_session_id_ctx('127.0.0.1:%s' % str(self.port))
        http.Server._setup_server(self)
        # Disable Netscape cipher reuse compatibility.
        ssl_ctx.set_options(0x00000FF7L)
        self.server.set_ssl_ctx(ssl_ctx)
        return
    def _certificate_maintenance(self):
        previous = PersistentDataObject(self)
        previous.cert_config = None
        previous.key_file = None
        previous.server_cert = None
        previous.cert_fingerprint = None
        previous.load()
        c = certificate.CertificateConfiguration(self)
        config = {'C':self.country}
        config['ST'] = self.state
        config['L'] = self.city
        config['O'] = self.organization
        config['OU'] = self.organizational_unit
        config['CN'] = self.common_name
        config['emailAddress'] = self.email
        c.configure(config)
        cert_fingerprint = makecert.get_fingerprint(self.server_cert)
        if previous.cert_fingerprint == cert_fingerprint:
           msglog.log('broadway', msglog.types.INFO, 'Certificate Fingerprint Match!!!!' )
        else:
           msglog.log('broadway', msglog.types.INFO, 'Certificate Fingerprint Mismatch!!!!' )
        if c == previous.cert_config and \
           previous.key_file == self.key_file and \
           previous.cert_fingerprint == cert_fingerprint and \
           not certificate.is_outdated(self.server_cert):
            msglog.log('broadway', msglog.types.INFO,
                       'Using existing certificate')
            return
        msglog.log('broadway', msglog.types.INFO, 'Generating new certificate')
        filename = os.path.join(properties.TEMP_DIR, 'cert_config.tmp')
        file = open(filename, 'w')
        c.formatted_output_to_file(file)
        try:
            failed = 1
            makecert.create_from_file(filename, self.key_file,
                                      self.server_cert)
            failed = 0
            msglog.log('broadway', msglog.types.INFO,
                       'Certificate generated')
        except:
            msglog.exception()
            msglog.log('broadway', msglog.types.WARN,
                       'Certificate generation failed')
        file.close()
        os.remove(filename)
        if not failed:
            previous.cert_config = c.configuration()
            previous.key_file = self.key_file
            previous.server_cert = self.server_cert
            previous.cert_fingerprint = makecert.get_fingerprint(self.server_cert)
            previous.save()
        return
def factory():
    return Server()
