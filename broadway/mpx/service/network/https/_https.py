"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import socket
import select
import asyncore
import asynchat
from threading import currentThread as current_thread
from errno import ENOTCONN
from errno import ESHUTDOWN
from errno import ECONNRESET
from M2Crypto import m2
from M2Crypto import SSL
from M2Crypto import Err
from M2Crypto import threading as m2threading
from mpx.lib import msglog
from mpx.service.network.http._http import HTTPServer
from mpx.service.network.http._http import VERSION_STRING
from mpx.service.network.http._http import Channel as HTTPChannel
EUNEXPECTEDEOF = "unexpected eof"
EBADCERTIFICATE = "alert bad certificate"
EUNKNOWNCERTIFICATE = "alert certificate unknown"
EUNKNOWNCA = "alert unknown ca"
acceptable_failures = (EBADCERTIFICATE,EUNKNOWNCERTIFICATE,EUNKNOWNCA)
try:
    # Initial cleanup in case of reloads 
    # or invocations by other clients.
    m2threading.cleanup()
except:
    pass
finally:
    # Iinitialize threading even though web-servers 
    # use M2Crypto within the context of only one thread, 
    # other clients such as sRNA may interfere with web-server 
    # if M2Crypto threading has not been initialized.
    m2threading.init()

class SSLOperationFailure(Exception):
    def __init__(self, operation, error, *args, **kw):
        self.error = error
        self.operation = operation
        super(SSLOperationFailure, self).__init__(*args, **kw)
    def __str__(self):
        typename = type(self).__name__
        return "%s %s: %r" % (typename, self.operation, self.error)
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))

class ESSLWantWrite(SSLOperationFailure):
    """
    """

class ESSLWantRead(SSLOperationFailure):
    """
    """

class Buffer(list):
    def __init__(self, bytes=None):
        self.contents = []
        self.content_length = 0
        if bytes:
            self.write(bytes)
        super(Buffer, self).__init__()
    def write(self, bytes):
        self.contents.append(bytes)
        self.content_length += len(bytes)
    def read(self, count=None):
        bytes = "".join(self.contents)
        self.drain()
        if count and count < len(bytes):
            self.write(bytes[count:])
            bytes = bytes[0: count]
        return bytes
    def drain(self):
        self.contents = []
        self.content_length = 0
    def __len__(self):
        return self.content_length

class Channel(HTTPChannel):
    ac_in_buffer_size = 1 << 14
    ac_out_buffer_size = 1 << 14
    def __init__(self, server, conn, addr):
        self._fileno = None
        self.ssl = None
        self.want_read = False
        self.want_write = False
        self.read_blocked = False
        self.write_blocked = False
        self.pending_write_buffer = ""
        self.read_blocked_on_read = False
        self.read_blocked_on_write = False
        self.write_blocked_on_read = False
        self.write_blocked_on_write = False
        self.watching_readable = False
        self.watching_writable = False
        self.error_occurred = False
        self.context = server.get_context()
        HTTPChannel.__init__(self, server, conn, addr)
    def set_socket(self, sock, *args):
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,self.linger)
        self._fileno = sock.fileno()
        self.socket = sock
        self.configure_ssl()
        self.ssl.setup_addr(self.addr)
        self.ssl.setup_ssl()
        self.set_accept_state()
        self.add_channel()
    def configure_ssl(self):
        self.ssl = SSL.Connection(self.context, self.socket)
        self.ssl_set_mode(self.ssl_get_mode() | 
                          m2.SSL_MODE_ENABLE_PARTIAL_WRITE | 
                          m2.SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER)
        self.ssl.setblocking(False)
    def ssl_get_mode(self):
        return m2.ssl_get_mode(self.ssl.ssl)
    def ssl_set_mode(self, mode):
        m2.ssl_set_mode(self.ssl.ssl, mode)
    def set_accept_state(self):
        self.accepted = False
        self.accepting = True
        self.ssl.set_accept_state()
    def readable(self):
        self.watching_readable = self.want_read or HTTPChannel.readable(self)
        return self.watching_readable
    def writable(self):
        self.watching_writable = self.want_write or HTTPChannel.writable(self)
        return self.watching_writable
    def handle_read_event(self):
        self.want_read = False
        if not self.ssl:
            self.log_debug("read-event ignored: no socket.", level=2)
        elif self.write_blocked_on_read:
            self.log_debug("read-event invoking handle-write", level=1)
            self.handle_write()
        elif self.write_blocked_on_write:
            self.log_debug("read-event ignored: write blocked.", level=2)
        elif self.read_blocked_on_write and self.want_write:
            self.log_debug("read-event ignored: read wait write.", level=2)
        else:
            self.log_debug("read-event propagating.", level=3)
            HTTPChannel.handle_read_event(self)
    def handle_write_event(self):
        self.want_write = False
        if not self.ssl:
            self.log_debug("write-event ignored: no socket.", level=2)
        elif self.read_blocked_on_write:
            self.log_debug("write-event invoking handle-read", level=1)
            self.handle_read()
        elif self.read_blocked_on_read:
            self.log_debug("read-event ignored: read blocked.", level=2)
        elif self.write_blocked_on_read and self.want_read:
            self.log_debug("write-event ignored: write wait read.", level=2)
        else:
            self.log_debug("write-event propagating.", level=3)
            HTTPChannel.handle_write_event(self)
    def handle_expt_event(self):
        """
            Normalize handling of POLLHUP, POLLPRI, and POLLERR 
            between poll() and select() based multiplexing.
            
            Using poll() can lead to I/O exceptional event in 
            scenarios where select() would indicate a socket 
            has become readable.  For example, POLLPRI indicates 
            readable in select; POLLHUP also results in select() 
            readable.  
            
            Depending upon timing conditions, these events may 
            be triggered without POLLIN also being flagged, such 
            as when not monitoring socket for readable I/O events.
            
            As a result situations which may normally be handled 
            by read returning empty string and closing a socket 
            normally, might be handled as and I/O exception event.
            
            This method uses select() to normalize the I/O event 
            and routes handling through the appropriate event handlers.
        """
        if not self.socket:
            self.log_debug("I/O exception event ignored: channel closed.")
            return
        state = "\n\t - ".join([""] + self.get_state())
        self.log_debug("handling I/O exception event: %s", state, level=1)
        fd = self._fileno
        try:
            readable,writable,exceptional = select.select([fd], [fd], [fd], 0)
        except:
            self.log_warning("select on file-descriptor failed.")
            self.handle_error()
            return
        if self.socket and readable:
            self.log_debug("readable: read-event", level=0)
            try:
                self.handle_read_event()
            except:
                self.handle_error()
                return
        if self.socket and writable:
            self.log_debug("writable: write-event", level=0)
            try:
                self.handle_write_event()
            except:
                self.handle_error()
                return
        if self.socket and exceptional:
            self.log_debug("exc: expt-event", level=0)
            try:
                self.handle_expt()
            except:
                self.handle_error()
                return
        if self.socket:
            message = "I/O exception event handling %r, %r, %r, left socket."
            self.log_error(message, readable, writable, exceptional)
            raise Exception("invalid socket state: %r,%r,%r")
        self.log_debug("I/O exception event handled.", level=0)
    def handle_accept(self):
        try:
            self.accepted = self.ssl.accept_ssl()
        except SSL.SSLError,error:
            if error[0] in (ECONNRESET,ENOTCONN,ESHUTDOWN,EUNEXPECTEDEOF):
                self.log_debug("SSL accept failed: %r." % error[0])
                logerror = False
            else:
                self.log_warning("SSL accept failed: %r." % error[0])
                if error[0].endswith(acceptable_failures):
                    logerror = False
                else:
                    logerror = True
            self.handle_error(logerror)
        else:
            self.log_debug("complete-ssl-accept: %r.", self.accepted, level=2)
        self.accepting = not self.accepted
    def handle_read(self):
        self.read_blocked_on_read = False
        self.read_blocked_on_write = False
        try:
            HTTPChannel.handle_read(self)
        except ESSLWantWrite,error:
            self.want_write = True
            self.read_blocked_on_write = True
            self.log_debug("handle-read retry: want-write.", level=2)
        except ESSLWantRead,error:
            self.want_read = True
            self.read_blocked_on_read = True
            self.log_debug("handle-read retry: want-read.", level=2)
        except SSLOperationFailure,error:
            self.log_warning("SSL read failed.  Exception follows.")
            msglog.exception(prefix="handled")
            self.handle_error(False)
        else:
            self.log_debug("handle-read succeeded.", level=3)
        self.log_debug("exit handle-read()", level=3)
    def handle_write(self):
        self.write_blocked_on_read = False
        self.write_blocked_on_write = False
        try:
            HTTPChannel.handle_write(self)
        except ESSLWantWrite,error:
            self.want_write = True
            self.write_blocked = True
            self.write_blocked_on_write = False
            self.log_debug("handle-write retry: want-write.", level=2)
        except ESSLWantRead,error:
            self.want_read = True
            self.write_blocked = True
            self.write_blocked_on_read = True
            self.log_debug("handle-write retry: want-read.", level=2)
        except SSLOperationFailure,error:
            self.log_warning("SSL write failed.  Exception follows.")
            msglog.exception(prefix="handled")
            self.handle_error(False)
        else:
            self.log_debug("handle-write succeeded.", level=3)
        self.log_debug("exit handle-write()", level=3)
    def handle_expt(self):
        if not self.socket:
            self.log_debug("handle-expt ignored: channel closed.", level=2)
            return
        self.log_warning("handle_expt() closing channel.")
        self.close()
    def handle_error(self, logerror=True):
        self.error_occurred = True
        state = "\n\t - ".join([""] + self.get_state())
        if not logerror:
            self.log_debug("handling error, state: %s", state, level=2)
        else:
            self.log_debug("handling error, state: %s", state, level=0)
            try:
                msglog.exception(msglog.types.ERR, None, 'Handled')
            except:
                self.log_warning("handle error failed to log details.")
                msglog.exception(prefix="handled")
        self.close()
    def handle_close(self):
        self.log_debug("handle-close called.", level=2)
        HTTPChannel.handle_close(self)
    def get_ssl_error(self, operation, returned):
        self.log_debug("%r operation: got %r.", operation, returned, level=3)
        try:
            errcode = self.ssl.ssl_get_error(returned)
        except Exception,error:
            if operation != "read":
                raise
            self.log_debug("Get error failed: assume want-read.", level=2)
            errcode = SSL.m2.ssl_error_want_read
        if errcode == SSL.m2.ssl_error_want_write:
            errtype = ESSLWantWrite
        elif errcode == SSL.m2.ssl_error_want_read:
            errtype = ESSLWantRead
        else:
            message = "SSL %r operation got %r: %r."
            self.log_error(message, operation, returned, errcode)
            errtype = SSLOperationFailure
        return errtype(operation, returned)
    def send(self, data):
        self.log_debug("send(%d bytes)", len(data), level=3)
        if self.write_blocked:
            pending = len(self.pending_write_buffer)
            message = "send() call pending: replacing %d bytes with %d."
            self.log_debug(message, len(data), pending, level=2)
            data = self.pending_write_buffer
        self.write_blocked = False
        self.pending_write_buffer = ""
        try:
            result = self.ssl.write(data)
        except SSL.SSLError,why:
            if why[0] in (ECONNRESET,ENOTCONN,ESHUTDOWN,EUNEXPECTEDEOF):
                self.log_debug('send() closing channel: %s.', why)
                self.close()
                return 0
            raise
        else:
            if result < 0:
                self.write_blocked = True
                self.pending_write_buffer = data
                raise self.get_ssl_error("write", result)
            elif result:
                self.server.bytes_out.increment(result)
        self.log_debug("send %d: sent %d.", len(data), result, level=2)
        return result
    def recv(self, bufsize):
        self.log_debug("recv(%d bytes)", bufsize, level=3)
        if self.read_blocked:
            self.log_debug("previous recv() call pending.", level=2)
        self.read_blocked = False
        try:
            result = self.ssl.read(bufsize)
            if result:
                # Replacing bufsize ensures that want-read/want-write
                # storage of pending arguments continues to function.
                pending = self.ssl.pending()
                if pending:
                    self.log_debug("reading pending %d.", pending, level=2)
                    result += self.ssl.read(pending)
        except SSL.SSLError,why:
            if why[0] in (ECONNRESET, ENOTCONN, ESHUTDOWN, EUNEXPECTEDEOF):
                self.log_debug('recv() closing channel: %s.', why, level=2)
                self.handle_close()
                return ""
            raise
        if not result:
            if result == "":
                self.log_debug("received '': closing channel.", level=2)
                self.handle_close()
            else:
                self.read_blocked = True
                raise self.get_ssl_error("read", result)
        else:
            count = len(result)
            self.server.bytes_in.increment(count)
            self.log_debug("recv %d: read %d.", bufsize, count, level=2)
        return result
    def close(self):
        if self.error_occurred:
            self.log_debug("closing SSL connection after error.")
        else:
            self.log_debug("closing SSL connection", level=3)
        if self.ssl:
            try:
                self.ssl.close()
            except:
                msglog.exception(prefix="handled")
        self.ssl = None
        self.context = None
        if self._current_request:
            try:
                self._current_request.handle_close()
            except:
                msglog.exception(prefix = 'handled')
        HTTPChannel.close(self)
        self.socket = None
    def __getattr__(self, name):
        self.log_debug("__getattr__(%r)", name)
        if self.ssl:
            try:
                attribute = getattr(self.ssl, name)
            except AttributeError:
                msglog.warn("Failed attribute lookup: %r." % name)
            else:
                return attribute
        return HTTPChannel.__getattr__(self, name)
    # The following methods should be migrated to HTTP Channel, 
    # but have been implemented here to isolate HTTPS fixes.
    def push_responses(self):
        pushed = 0
        requests = self._request_queue
        while requests[0].writable():
            self.producer_fifo.push(requests.pop(0).out)
            self.response_counter.increment()
            pushed += 1
        if requests[0] is self._null_request and not self._keep_alive:
            self.producer_fifo.push(None)
        if pushed:
            # Discards final call to make averages more pertinent
            self.buffer_refills.increment()
        else:
            self.refill_skips.increment()
        return pushed
    def refill_buffer(self):
        """
            Overrides async-chat's refill-buffer so that buffer is 
            refilled until no more outgoing content is ready, or 
            the outgoing buffer's size is equal to or greater than 
            the maximum outgoing buffer.
            
            Note that this also causes spent producers to be discarded 
            without always requiring an extra write loop poll, as the 
            method no longer exits after pulling data from the first 
            available producer.
        """
        self.push_responses()
        producers = self.producer_fifo
        while producers and len(self.ac_out_buffer) < self.ac_out_buffer_size:
            producer = producers.first()
            if producer is None:
                if not self.ac_out_buffer:
                    producers.pop()
                    self.close()
                break
            if isinstance(producer, str):
                producers.pop()
                self.ac_out_buffer = self.ac_out_buffer + producer
            else:
                data = producer.more()
                if data:
                    self.ac_out_buffer = self.ac_out_buffer + data
                else:
                    producers.pop()
    def get_state(self):
        """
            Get list of strings describing state of I/O flags.
        """
        stats = ["Want read: %r" % self.want_read]
        stats.append("Want write: %r" % self.want_write)
        stats.append("Read waiting: %r" % self.read_blocked)
        stats.append("Read wait on read: %r" % self.read_blocked_on_read)
        stats.append("Read wait on write: %r" % self.read_blocked_on_write)
        stats.append("Write waiting: %r" % self.write_blocked)
        stats.append("Write wait on read: %r" % self.write_blocked_on_read)
        stats.append("Write wait on write: %r" % self.write_blocked_on_write)
        stats.append("Notify on readable: %r" % self.watching_readable)
        stats.append("Notify on writable: %r" % self.watching_writable)
        stats.append("Has socket: %r" % (self.socket is not None))
        stats.append("Has ssl: %r" % (self.ssl is not None))
        stats.append("File-descriptor: %r" % (self._fileno))
        return stats
    def log(self, *args):
        self.log_warning("log called: %r." % (args,))
    def log_info(self, message, type=msglog.types.INFO):
        if type == msglog.types.DB and not self.server.debug:
            return
        typename = self.__class__.__name__
        prefix = '%s(%s #%d)' % (self.server, typename, self.channel_number)
        msglog.log(prefix, type, message)
    def log_warning(self, message, *args):
        if args:
            message = message % args
        self.log_info(message, msglog.types.WARN)
    def log_error(self, message, *args):
        if args:
            message = message % args
        self.log_info(message, msglog.types.ERR)
    def log_debug(self, message, *args, **kw):
        if kw.get("level", 1) <= self.server.debug:
            if args:
                message = message % args
            self.log_info(message, msglog.types.DB)
            return True
        return False

class HTTPSServer(HTTPServer):
    PROTOCOL = "HTTPS"
    channel_class=Channel
    SERVER_IDENT = 'HTTPS Server (%s)' % VERSION_STRING
    def __init__(self, ip, port, user_manager, realm, 
                 authentication, maintenance_interval=25, 
                 zombie_timeout=600, debug=0, ssl_ctx=None):
        HTTPServer.__init__(self, ip, port, user_manager, realm, 
                            authentication, maintenance_interval, 
                            zombie_timeout, debug)
        self.ssl_ctx=ssl_ctx
    def set_context(self, context):
        self.ssl_ctx = context
    def get_context(self):
        return self.ssl_ctx
    def set_ssl_ctx(self, ssl_ctx):
        self.set_context(ssl_ctx)
    def log_warning(self, message):
        self.log_info(message, msglog.types.WARN)


