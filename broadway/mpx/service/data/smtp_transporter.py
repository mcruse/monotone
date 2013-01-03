"""
Copyright (C) 2002 2003 2006 2007 2009 2010 2011 Cisco Systems

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
import array
import string
import time

from email.MIMEText import MIMEText
from email.Utils import make_msgid
from email.Utils import formatdate

from mpx.lib import msglog,smtplib
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.configure import as_boolean
from mpx.lib.configure import as_onoff
from mpx.lib.configure import stripped_str
from mpx.lib.exceptions import MpxException
from mpx.lib.node import as_node
from mpx.service.data import Transporter

from _transporter_exceptions import *

COMMASPACE = ', '

class SMTPTransporter(Transporter):
    SMTP = smtplib.SMTP
    def configure(self,config):
        set_attribute(self,'debug',0,config,int)
        set_attribute(self,'host',REQUIRED,config)
        set_attribute(self,'port',25,config,int)
        set_attribute(self,'authenticate',0,config,as_boolean)
        set_attribute(self,'username','',config)
        set_attribute(self,'password','',config)
        set_attribute(self,'sender',REQUIRED,config)
        set_attribute(self,'recipients',REQUIRED,config)
        set_attribute(self,'subject','',config)
        #CSCtg54123
        if (config.has_key('timeout') and config['timeout'] == ''):
            config['timeout'] = 'None'
        set_attribute(self,'timeout',None,config,float)
        set_attribute(self,'custom_domain', "", config, stripped_str)
        set_attribute(self,'as_attachment',0,config,as_boolean)
        set_attribute(self,'subtype','',config)
        if self.subtype not in ('', 'plain', 'html', 'xml'):
            raise ValueError('Subtype must be plain, html, or xml.')
        self._recipients = []
        if hasattr(self, 'recipients'):
            for recipient in string.split(self.recipients,','):
                self._recipients.append(string.strip(recipient))
        Transporter.configure(self, config)
    def configuration(self):
        config = Transporter.configuration(self)
        get_attribute(self,'debug',config)
        get_attribute(self,'host',config)
        get_attribute(self,'port',config,str)
        get_attribute(self,'authenticate',config,str)
        get_attribute(self,'username',config)
        get_attribute(self,'password',config)
        get_attribute(self,'sender',config)
        get_attribute(self,'recipients',config)
        get_attribute(self,'subject',config)
        get_attribute(self,'timeout',config,str)
        get_attribute(self,'custom_domain', config, str)
        get_attribute(self,'as_attachment',config,str)
        get_attribute(self,'subtype', config)
        return config
    # @todo Look at using streaming data with smtp.
    def transport(self, data):
        if type(data) != type(''):
            # @todo Add warning that stream is being ignored
            # @todo Assuming that not string means stream.
            a = array.array('c')
            stream_data = data.read(1024)
            while stream_data:
                a.fromstring(stream_data)
                stream_data = data.read(1024)
            data = a.tostring()

        headers = {}
        splitdata = data.split('\r\n\r\n')
        if len(splitdata) > 1:
            headerdata = splitdata[0]
            data = string.join(splitdata[1:], '\r\n\r\n')
            for header in headerdata.split('\r\n'):
                splitheader = header.split(':')
                name = splitheader[0].strip()
                value = string.join(splitheader[1:], ':').strip()
                headers[name] = value

        if self.subtype:
            text_subtype = self.subtype
        else: text_subtype = 'plain'
        if text_subtype == 'plain':
            default_extension = 'txt'
        else:
            default_extension = text_subtype
        if text_subtype != 'xml' and data[:16].strip()[:5] == '<?xml':
            msglog.log('broadway', msglog.types.WARN,
                       'Transporter overriding configured subtype to "xml".')
            text_subtype='xml'
            default_extension = 'xml'
        msg = MIMEText(data, _subtype=text_subtype)
        subject = headers.get('Subject')
        if subject is None or subject == 'None' or subject == '':
            subject = self.subject
        #CSCtg54105
        else:
            if self.subject is not None and self.subject != 'None' and self.subject != '':
                subject = self.subject + ': ' + subject
        if subject:
            msg.add_header('Thread-Topic', subject)
            msg.add_header('Subject', subject)
        msg.add_header('From', self.sender)
        msg.add_header('To', COMMASPACE.join(self._recipients))
        date = headers.get('Date', formatdate(time.time(), True))
        msg.add_header('Date', date)

        message_id = make_msgid()
        if self.as_attachment:
            # @fixme: Make configurable
            default_filename = "%s.%s" % (
                message_id[1:-1].split("@")[0],
                default_extension
                )
            msg.add_header('Content-Disposition', 'attachment',
                           filename=default_filename)
            msg.set_param('name',  default_filename)
        # @fixme: Make configurable
        msg.add_header('Content-Class', 'urn:content-classes:message')
        # @fixme: Make configurable
        msg.add_header('X-Mailer', 'Mediator SMTP Transport')
        msg.add_header('Message-ID', message_id)
        # @fixme: Make configurable
        msg.add_header('Importance', 'normal')
        # @fixme: Make configurable
        msg.add_header('Priority', 'normal')
        msg.preamble = ''
        # To guarantee the message ends with a newline
        msg.epilogue = ''

        smtp = self.SMTP()
        if self.debug:
            smtp.set_debuglevel(self.debug)
        smtp.connect(self.host,self.port,self.timeout)
        if self.custom_domain:
            if not (200 <= smtp.ehlo(self.custom_domain)[0] <= 299):
                (code, resp) = smtp.helo(self.custom_domain)
                if not (200 <= code <= 299):
                    raise smtp.SMTPHeloError(code, resp)
        if self.authenticate:
            try:
                smtp.login(self.username,self.password)
            except smtplib.SMTPAuthenticationError:
                msglog.log('broadway',msglog.types.WARN,
                           'SMTP Authentication failed.' +
                           '  Invalid username/password.')
                raise
        failures = smtp.sendmail(self.sender,self._recipients,
                                 msg.as_string())
        for recipient in failures.keys():
            msglog.log('broadway',msglog.types.WARN,
                       'Error sending mail to %s -> %s' %
                       (recipient,failures[recipient]))
        smtp.close()
