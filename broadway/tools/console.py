"""
Copyright (C) 2008 2009 2010 2011 Cisco Systems

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
#!/usr/bin/env python-mpx
import sys
import socket
import urllib
import readline
import errno
from threading import Event
from threading import Thread

class EndSession(Exception):
    def __init__(self, source, reason=""):
        self.source = source
        self.reason = reason
        super(EndSession, self).__init__(source, reason)
    def __str__(self):
        typename = type(self).__name__
        sourcename = type(self.source).__name__
        return "%s(%s, %r)" % (typename, sourcename, self.reason)
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))

class Console(object):
    def __init__(self, connection):
        self.connection = connection
        self.reader = Reader(connection)
        self.writer = Writer(connection)
        super(Console, self).__init__()
    def run(self):
        self.reader.setDaemon(True)
        self.reader.start()
        self.loop()
    def loop(self):
        while True:
            try:
                self.await_response()
                command = self.get_command()
                self.send_command(command)
            except EndSession, reason:
                print "\n", reason
                break
        print "Console Session ending: good bye."
    def get_command(self):
        try:
            command = raw_input()
        except EOFError:
            raise EndSession(self, "<Crtl-d> received")
        return command
    def send_command(self, line):
        self.writer.write(line)
    def await_response(self):
        return self.reader.await_response(20)

class Reader(Thread):
    def __init__(self, connection):
        self.connection = connection
        self.response_handled = Event()
        self.connection_terminated = Event()
        super(Reader, self).__init__()
    def running(self):
        return self.isAlive()
    def await_response(self, timeout=None):
        self.response_handled.wait(timeout)
        if self.connection_terminated.isSet():
            raise EndSession(self, "Remote connection closed.")
        self.response_handled.clear()
    def run(self):
        try:
            while True:
                line = ""
                while not line.endswith("\r\n"):
                    try:
                        data = self.connection.recv(1024)
                    except socket.error, error:
                        if error.args and error.args[0] == errno.EINTR:
                            continue
                        raise
                    if not data:
                        break
                    line += data
                if not line:
                    break
                self.handle_quoted(line.strip())
        finally:
            self.connection_terminated.set()
            self.response_handled.set()
    def handle_quoted(self, data):
        response = urllib.unquote(data)
        self.handle_response(response)
    def handle_response(self, response):
        self.output_response(response)
        self.response_handled.set()
    def output_response(self, response):
        sys.stdout.write(response)
        sys.stdout.flush()

class Writer(object):
    def __init__(self, connection):
        self.connection = connection
        super(Writer, self).__init__()
    def write(self, data):
        quoted = urllib.quote(data) + "\r\n"
        try:
            sent = self.connection.send(quoted)
        except socket.error, error:
            if error.args and error.args[0] == errno.EINTR:
                return 0
            if isinstance(error, tuple) and error[0] == 32:
                message = "Connection closed remotely."
                raise EndSession(self, message)
            raise
        return sent

def runconsole():
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.connect(('localhost', 9666))
    console = Console(connection)
    console.run()

if __name__ == "__main__":
    runconsole()
