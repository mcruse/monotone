"""
Copyright (C) 2001 2002 2003 2005 2008 2009 2010 2011 Cisco Systems

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
##
# @fixme If start fails to bind to a port, go into a background persistant
#        retry (but return).
import socket
import types
import sys
import os
import os.path
import errno
import mpx.lib
import mpx.lib.rna
from mpx.lib import pause
from mpx.lib.threading import Thread
from mpx.lib.thread_pool import ThreadPool
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.service import ServiceNode
from mpx.lib.rna import SimpleTcpService
from mpx.lib.rna import SrnaService
from mpx.lib.rna import SimpleSocketSession
from mpx.lib.rna import SrnaSession
from mpx.lib.rna import SimpleTextProtocol, ProtocolResult, ProtocolCommand
from mpx.lib.rna_xml import ProtocolInterfaceImplXML
from mpx.lib import msglog, thread
from mpx.lib.exceptions import EInvalidMessage
from mpx.lib.exceptions import EInvalidProtocol
from mpx.lib.exceptions import ETimeout
from mpx.lib.security import RExec
from mpx.service.network.async.connection.trigger import Trigger
try:
    SocketTimeoutError = socket.timeout
except:
    SocketTimeoutError = ETimeout

##
# Invoke a command on a <code>Node</code> and return the result.
# 
# Any exception that occurs is caught and formated by the command object
# this allows for 'Protocol' specific handling of exceptions.
#
# @param command  The <code>mpx.lib.rna._InvokeCommand</code> object
#                 containing the command that has been invoked remotely.
#
# @return {@link mpx.lib.rna.ProtocolResult ProtocolResult} object containing
#         the information returned by the invoked command.
#
def _invoke_command(command):
    service   = 'protocol failure'
    method    = service
    result    = repr(None)
    exception = repr(None)
    try:
        service = command.service        # URI to the target node.
        method = command.method            # Name of method to invoke.
        
        s = mpx.lib.node.as_node(service)    # Reference to the node.
        bound_func = getattr(s,method)        # Ref. to node's bound method.
        args = command.get_arguments()        # Arguments converted to a
                        # Python list.
        # Invoke the bound method with the passed arguments.
        result = apply(bound_func,args)
    except Exception, e:
        exception = command.formatException(e, e.args, None)
    except:
        e, args, tbo = sys.exc_info()
        exception = command.formatException(e, args, tbo)
    return ProtocolResult(service,method,result,exception)

##
# Loop that listens at a port for commands to come.
#
# @param rna_service  The {@link RNA RNA} service that
#                     started this thread.
#
# @note When a command is received it is invoked,
#       and the result is sent back to the caller.
#
import select
from threading import RLock, Condition, Event # SHP
import Queue
from time import time
import time as time_mod
from mpx import properties as props
from os.path import join

class RNA_Scan_Thread(Thread):
    """ Polls for and handles any incoming msgs from established RNA sockets
    connected to clients."""
    def __init__(self, name='RNA_Scan_Thread'):
        pfx = 'RNA_Scan_Thread.__init__:' 
        msg = '%s Entering...' % pfx
        msglog.log('broadway', msglog.types.INFO, msg)
        self.debug = 0
        
        # Maps file-descriptors to host-names.
        self.hosts = {}
        # Maps file-descriptors to sessions.
        self.sessions = {}
        # Maps host-names to sets of file-descriptors
        self.socketmap = {}
        self.connections = {}
        self.bPollRun = False
        self.work_queue = None
        self.descriptors = set()
        self.trigger_channel = Trigger(self.socketmap)
        self.descriptors.add(self.trigger_channel.fileno())
        msg = '%s Done.' % pfx
        msglog.log('broadway', msglog.types.INFO, msg)
        super(RNA_Scan_Thread, self).__init__(name=name)
    def start(self):
        self.bPollRun = True
        if not self.work_queue:
            self.work_queue = ThreadPool(5)
        else:
            self.work_queue.resize(5)
        # Superclass calls run() on separate thread:
        return super(RNA_Scan_Thread, self).start() 
    def stop(self):
        self.bPollRun = False
        self.notify_poll()
        self.work_queue.resize(0)
        return super(RNA_Scan_Thread, self).stop()
    def is_running(self):
        return self.isAlive()
    def run(self):
        pfx = 'RNA_Scan_Thread.run:'
        cmdfd = self.trigger_channel.fileno()
        enqueue = self.work_queue.queue_noresult
        handle_session = self.handle_session_input
        clear_notifications = self.clear_notifications
        while self.bPollRun:
            try:
                descriptors = self.descriptors.copy()
                if cmdfd not in descriptors:
                    msglog.warn("Command channel FD removed!")
                    descriptors.add(cmdfd)
                r,w,e = select.select(descriptors, [], descriptors, 1)
                for fd in e:
                    if fd == cmdfd:
                        message = "%s internal polling error.  Must restart."
                        msglog.error(message % pfx)
                        raise TypeError("command channel OOB data")
                    try:
                        self.unregister_session(self.get_session(fd))
                    except:
                        msglog.warn("%s I/O event handling error." % pfx)
                        msglog.exception(prefix="handled")
                for fd in r:
                    if fd in self.descriptors:
                        try:
                            if fd == cmdfd:
                                clear_notifications()
                            else:
                                self.descriptors.discard(fd)
                                enqueue(handle_session, fd)
                        except:
                            msglog.warn("%s I/O event handling error." % pfx)
                            msglog.exception(prefix="handled")
            except:
                msglog.warn("%s loop error." % pfx)
                msglog.exception(prefix="handled")
        msglog.inform("%s exiting." % pfx)
    def notify_poll(self):
        self.trigger_channel.trigger_event()
    def clear_notifications(self):
        self.trigger_channel.handle_read()
    def register_session(self, session):
        try:
            fd = session.socket.fileno()
            host,port = session.socket.getpeername()
        except:
            msglog.warn("Failed to add session: %r" % session)
            msglog.exception(prefix="handled")
            registered = False
        else:
            self.hosts[fd] = host
            self.sessions[fd] = session
            self.connections.setdefault(host, set()).add(fd)
            self.descriptors.add(fd)
            self.notify_poll()
            registered = True
        return registered
    def unregister_session(self, session):
        try:
            fd = session.socket.fileno()
        except:
            unregistered = False
        else:
            host = self.hosts.pop(fd, None)
            if host is not None:
                connections = self.connections.get(host, None)
                if connections is not None:
                    connections.discard(fd)
                    if not connections:
                        self.connections.pop(host, None)
            self.sessions.pop(fd, None)
            if fd in self.descriptors:
                self.descriptors.discard(fd)
                self.notify_poll()
            try:
                session.disconnect()
            except:
                msglog.exception(prefix="handled")
            unregistered = True
        return unregistered
    def get_session(self, fd):
        if not isinstance(fd, int):
            fd = fd.fileno()
        return self.sessions[fd]
    def get_host(self, fd):
        if not isinstance(fd, int):
            fd = fd.fileno()
        return self.hosts[fd]
    def get_connections(self, host):
        return self.connections.get(host, [])
    def has_connections(self, host):
        return host in self.connections
    def get_sessions(self, host):
        connections = self.get_connections(host)
        return map(self.get_session, connections)
    def handle_session_input(self, fd):
        pfx = 'RNA_Scan_Thread.handle_session_input'
        unregister = False
        session = self.get_session(fd)
        try:
            rna_header = RNAHeader(session.socket)
            protocol = _protocol_factory(rna_header.protocol)
            protocol.setup(session, rna_header)
            command = protocol.recv_command()
            result = _invoke_command(command)
            protocol.send_result(command, result)
        except EInvalidMessage, error:
            if not error.message:
                unregister = True
                msglog.warn("Removing client-closed session: %s" % session)
            else:
                unregister = False
                msglog.exception(prefix="handled")
        except SocketTimeoutError:
            unregister = False
            message.exception(prefix="handled")
        except:
            unregister = True
            msglog.exception(prefix="handled")
        else:
            unregister = False
        finally:
            if unregister:
                self.unregister_session(session)
            else:
                self.descriptors.add(fd)
                self.notify_poll()

class RNA_Thread(Thread):
    def __init__(self, rna_service, name='RNA_Thread'):
        self.rna_service = rna_service
        Thread.__init__(self, name=name)
        self.rna_scan_thread = RNA_Scan_Thread()
    def _cleanup(self, msg_type=msglog.types.ERR):
        # Stop rna_scan_thread:
        # TODO: ...
        rna_service = self.rna_service
        msglog.log('broadway', msg_type, 'RNA thread terminating.')
        try:
            rna_service.transport.destroy()
            rna_service.transport = None
        except:
            msglog.exception()
        rna_service.state = rna_service.STOPPED
        return
    def bound_port(self):
        return self.rna_service.transport.bound_port()
    def start(self):
        self.rna_scan_thread.start()
        return super(RNA_Thread, self).start()
    def run(self):
        rna_service = self.rna_service
        msglog.log('broadway', msglog.types.INFO, 'RNA thread starting.')
        try:
            rna_service.transport.listen()
        except:
            msglog.exception()
            self._cleanup()
            return
        nexceptions = 0
        texceptions = 0
        if rna_service.state is rna_service.PENDING:
            rna_service.state = rna_service.RUNNING
        while rna_service.state is rna_service.RUNNING:
            if not self.rna_scan_thread.is_running():
                msglog.warn("%s scan thread not running: exiting." % self)
                break
            try:
                session = rna_service.transport.accept_session()
                self.rna_scan_thread.register_session(session)
            except:
                msglog.exception(prefix='handled')
        self._cleanup(msglog.types.INFO)
##
# RNA sub-service.  Allows commands to be invoked on
# <code>Nodes</code> remotely.
#
class RNA_Socket(ServiceNode):
    STOPPED = 'STOPPED'
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    HALTING = 'HALTING'
    def __init__(self):
        ServiceNode.__init__(self)
        self.transportClass = None # can't be set until we configure security
        self.was_enabled = 0
        self.enabled = 0
        self.start_count = 0
        self.stop_count = 0
        self.state = self.STOPPED
        self.debug = 0
        self.__rna_thread = None
        return
    def bound_port(self):
        if self.port == 0:
            return self.__rna_thread.bound_port()
        return self.port
    def configure(self, config):
        ServiceNode.configure(self, config)
        set_attribute(self, 'security_level', 'NoSec', config)
        msglog.log('broadway', msglog.types.INFO,
                   'RNA_Socket.configure: security_level = %s.' % self.security_level)
        self.transportClass = SimpleTcpService
        if (self.security_level == 'Auth-Only') \
            or (self.security_level == 'Full-Enc'):
            self.transportClass = SrnaService
        # Handle changes to the enabled attribute, once we've started.
        if self.enabled != self.was_enabled:
            if self.enabled:
                if self.start_count and self._start():
                    self.start_count += 1
                    self.was_enabled = self.enabled
            elif self.start_count > self.stop_count:
                self.stop_count += 1
                self._stop()
        return
    def configuration(self):
        config = ServiceNode.configuration(self)
        get_attribute(self, 'security_level', config, str)
        return config
    def _stop(self):
        while self.state is self.PENDING:
            pause(.1)
        if self.state is not self.STOPPED:
            self.state = self.HALTING
            msg = 'RNA service stopping on %s.'
            msglog.log('broadway', msglog.types.INFO, msg % self.transport)
            try:
                # Hack to wake up the tread...
                t = self.transportClass(**self.configuration())
                # TODO: THIS CANNOT WORK. Neither SimpleTcpService nor 
                # SrnaService has a connect() method:
                t.connect()
                i = mpx.lib.rna._InvokeCommand("BOGUS")
                i.pack(ProtocolCommand('/','no_such_method_i_hope',()))
                i.totransport(t.send)
                # TODO: THIS CANNOT WORK. Neither SimpleTcpService nor 
                # SrnaService has a disconnect() method:
                t.disconnect()
                while self.state is not self.STOPPED:
                    pause(.1)
                    return 1
            except:
                msglog.exception()
        return 0
    def _start(self):
        if self.state is self.STOPPED:
            try:
                self.transport = self.transportClass(**self.configuration())
                msg = 'RNA service starting on %s.'
                msglog.log('broadway', msglog.types.INFO,
                           msg % self.transport)
                self.state = self.PENDING
                # RNA_Thread ctor creates RNA_Scan_Thread whose ctor can raise
                # exceptions (eg if remnant UNIX sockets cannot be removed):
                self.__rna_thread = RNA_Thread(self, name='RNA_Thread')
                self.__rna_thread.start()
            except:
                msglog.exception()
                msglog.log('broadway', msglog.types.ERR,
                           'RNA service could not be started.')
                self._stop()
                return 0
        return 1
    ##
    # Start RNA Service running and listening for commands
    # on the configured port.
    #
    def start(self):
        if self.enabled:
            self.start_count += 1
            self._start()
        ServiceNode.start(self)
        return
    def stop(self):
        if self.enabled:
            self.stop_count += 1
            self._stop()
        ServiceNode.stop(self)
        return
##
# RNA sub-service.  Allows commands to be invoked on
# <code>Nodes</code> remotely.
#
class RNA_Tcp(RNA_Socket):
    def __init__(self):
        RNA_Socket.__init__(self)
        return
    ##
    # Configures the RNA sub-service.
    #
    # @param config  Dictionary holding configuration.
    # @key port  Port to listen on for incomming requests.
    # @default 5150
    # @param client_connect_timeout The default timeout for CLIENT side
    #        connect()s to remote Mediators.
    # @default mpx.lib.rna.DEFAULT_CONNECT_TIMEOUT (3)
    # @param client_transaction_timeout The default timeout for CLIENT side
    #        recv() and send()s to complete.
    # @default mpx.lib.rna.DEFAULT_TRANSACTION_TIMEOUT (900)
    def configure(self, config):
        RNA_Socket.configure(self, config)
        set_attribute(self, 'interface', 'all', config)
        set_attribute(self, 'port', SimpleTcpService.DEFAULT_PORT,
                      config, int)
        #
        # Update default client RNA timeout.
        #
        set_attribute(self, 'client_connect_timeout',
                      mpx.lib.rna.DEFAULT_CONNECT_TIMEOUT,
                      config, float)
        mpx.lib.rna.DEFAULT_CONNECT_TIMEOUT = self.client_connect_timeout
        set_attribute(self, 'client_transaction_timeout',
                      mpx.lib.rna.DEFAULT_TRANSACTION_TIMEOUT,
                      config, float)
        mpx.lib.rna.DEFAULT_TRANSACTION_TIMEOUT = \
            self.client_transaction_timeout
        return
    ##
    # Get configuration of this Object.
    #
    # @return Dictionary containing configuration.
    #
    def configuration(self):
        config = RNA_Socket.configuration(self)
        get_attribute(self, 'port', config, str)
        get_attribute(self, 'interface', config, str)
        return config

def factory():
    return RNA_Tcp()

##
# RNA Header object
# used to read an RNA header object 
# from an open connection and encapsulate
# the various pieces of information found.
#
# @notes  A test RNAHeader can be created by
#         setting Socket == None and length > 0
#
class RNAHeader:
    SEP = ':'
    ISEP1 = 3
    ISEP2 = ISEP1+6+1
    ISEP3 = ISEP2+7+1
    # LENGTH = MSG:INVOKE:1234567 (PROTOCOL-3:TYPE-5:LENGTH_OF_PAYLOAD-7)
    HEADER_LENGTH = 19 
    def __init__(self, sock):
        command = "COMMAND"
        protocol = "PROTOCOL"
        if(sock == None):
            return
        retry_count = 0
        data = ''
        # Although the following calls can throw Exceptions, we want them
        # caught by the callers, not by this ctor.
        # Read header from incoming socket
        while (len(data) < self.HEADER_LENGTH) and (retry_count < 10):
            # Call to recv() blocks for up to preset timeout sec:
            data += sock.recv(self.HEADER_LENGTH - len(data))
            retry_count += 1
        if (len(data) < self.HEADER_LENGTH 
            or data[self.ISEP1] != self.SEP
            or data[self.ISEP2] != self.SEP
            or data[self.ISEP3] != self.SEP):
            raise EInvalidMessage(data)
        self.protocol = data[0:self.ISEP1] 
        self.command = data[self.ISEP1+1:self.ISEP2]
        self.len = int(data[self.ISEP2+1:self.ISEP3])
        self.buffer = None
        return


## _protocol_factory is used to create the appropriate Protocol
#  to process the RNA command.  
#  Each protocol implement ProtocolInterface and must except an 
#  empty constructor.   The appropriate values are setup via the 
#  'setup() method' on the ProtocolInterface.  This method should
#  be overridden by each ProtocolInterface implemenation

_protocol_dictionary = {'MSG':SimpleTextProtocol, 
                        'XML':ProtocolInterfaceImplXML}

def _protocol_factory(protocol_key):
    if(_protocol_dictionary.has_key(protocol_key)):
        return _protocol_dictionary[protocol_key]()
    else:
        raise EInvalidProtocol(protocol_key)
