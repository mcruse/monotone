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
from mpx.service.data import smtp_transporter
from mpx.lib.node import ConfigurableNode

import trap_exporter
import smtp_formatter
import trap_log

from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

PRINT_SENDMAIL=0

def trap_log_factory(parent=None, name='trap_log'):
    log = trap_log.TrapLog()
    log.configure({'parent':parent, 'name':name})
    columns = trap_log.TrapColumns()
    columns.configure({'parent':log, 'name':'columns'})
    exporters = trap_log.TrapExporters()
    exporters.configure({'parent':log, 'name':'exporters'})
    column_dict = {
        'address':trap_log.TrapAddressColumn,
        'context_engine_id':trap_log.TrapContextEngineIdColumn,
        'context_name':trap_log.TrapContextNameColumn,
        'logtime':trap_log.TrapLogTimeColumn,
        'sysUpTime':trap_log.TrapSysUpTimeColumn,
        'trap':trap_log.TrapTrapColumn,
        'trap_enterprise':trap_log.TrapTrapEnterpriseColumn,
        'varBinds':trap_log.TrapVarBindsColumn,
        'version':trap_log.TrapVersionColumn,
        }
    for name, klass in column_dict.items():
        column = klass()
        column.configure({'parent':columns, 'name':name})
    return log

class TrapTestFormatter(smtp_formatter.TrapFormatter):
    def start(self):
        smtp_formatter.TrapFormatter.start(self)
        return

class SMTPTestStub(object):
    def set_debuglevel(self, debug):
        return
    def connect(self, host, port, timeout):
        return
    def ehlo(self, domain):
        return
    def helo(self, domain):
        return
    def SMTPHeloError(self, code, resp):
        return
    def login(self, username, password):
        return
    def sendmail(self, sender, _recipients, msg):
        if PRINT_SENDMAIL:
            print "sendmail sender - :",sender
            print "sendmail _recipients - :",_recipients
            print "sendmail - msg:",msg
        return {}
    def close(self):
        return

class TestSMTPTransporter(smtp_transporter.SMTPTransporter):
    SMTP = SMTPTestStub
    def __init__(self):
        self.host = None
        self.sender = None
        self.recipients = ''
        return
    def configure(self, cd):
        smtp_transporter.SMTPTransporter.configure(self, cd)
        return
    def start(self):
        smtp_transporter.SMTPTransporter.start(self)
        return

def trap_exporter_factory(parent=None, name='trap_exporter'):
    class ConnectionNode(ConfigurableNode):
        def acquire(self):
            return True
        def release(self):
            return
    connection_node = ConnectionNode()
    exporter = trap_exporter.TrapExporter()
    exporter.configure({'parent':parent, 'name':name,
                        'connection_node':connection_node})
    formatter = TrapTestFormatter()
    formatter.configure({'parent':exporter, 'name':'smtp_formatter'})
    transporter = TestSMTPTransporter()
    transporter.configure({'parent':exporter, 'name':'smtp_transporter'})
    return exporter
