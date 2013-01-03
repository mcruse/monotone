"""
Copyright (C) 2007 2009 2010 2011 Cisco Systems

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
import errno
import os
import popen2
import signal
import time

from mpx import properties

from mpx.lib import Result
from mpx.lib import msglog

from mpx.lib.node import Node

from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.configure import set_attributes, get_attributes, as_boolean

from mpx.lib.exceptions import EInvalidMessage
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import Unauthorized

from mpx.lib.threading import Lock

from network import Network 
from application import Application
from group import Group
from level import Level

CBUS_CLI = os.path.join(properties.BIN_DIR, 'cbus_cli')

class CBus(Node):
    __node_id__ = "50b9f586-fe01-4c1b-a92a-dc5b27b7567e"
    PROMPT = "ready>\n"
    def __init__(self):
        Node.__init__(self)
        self._dev_name = None # Can programmatically override BEFORE start.
        self._lock = Lock()
        self._popen = None
        self._apps = []
        self._groups = []
        self._discovery_ts = None
        return
    def _get_dev_name(self):
        if self._dev_name:
            return self._dev_name
        self._dev_name = self.parent.dev
        return self._dev_name
    def configure(self,config):
        Node.configure(self,config)
        set_attribute(self, 'auto_discover', 1, config, as_boolean)
        set_attribute(self, 'debug', 0, config, as_boolean)
        return
    def configuration(self):
        config = Node.configuration(self)
        get_attribute(self, 'auto_discover', config)
        get_attribute(self, 'debug', config)
        return config
    def _restart(self):
        assert self._lock.locked()
        self._reset_popen()
        self._popen = popen2.Popen3(
            "superexec %s %s" % (CBUS_CLI, self._get_dev_name()), False
            )
        line = self._popen.fromchild.readline()
        if self.debug:
            print "< %r" % line
        while (line and line != CBus.PROMPT):
            line = self._popen.fromchild.readline()
            if self.debug:
                print "< %r" % line
        if self.auto_discover:
            # This is really a work around to how CBM discovers initial values.
            self._discover()
        return
    def start(self):
        self._lock.acquire()
        try:
            self._restart()
        finally:
            self._lock.release()
        Node.start(self)
        return
    def stop(self):
        self._lock.acquire()
        try:
            self._reset_popen()
            self._dev_name = None
            self._discovery_ts = None
        finally:
            self._lock.release()
        Node.stop(self)
        return
    def _reset_popen(self):
        if (self._popen is not None):
            try:
                os.kill(self._popen.pid, signal.SIGTERM)
            except OSError, e:
                if e.errno != errno.ESRCH:
                    raise
            try:
                self._popen.wait()
            except OSError, e:
                if e.errno != errno.ECHILD:
                    raise
            self._popen = None
        return
    def _invoke_blocking_command(self, cmd):
        assert self._lock.locked()
        result = []
        if self.debug:
            print "> %r" % cmd
        self._popen.tochild.write(cmd)
        self._popen.tochild.flush()
        line = self._popen.fromchild.readline()
        if self.debug:
            print "< %r" % line
        while (line and line != CBus.PROMPT):
            line = line[:-1] # Eat the \n, yum!
            if (line):
                result.append(line)
            line = self._popen.fromchild.readline()
            if self.debug:
                print "< %r" % line
        return result
    def blocking_command(self, cmd, unlocked=True):
        assert cmd[-1] == '\n'
        try:
            if unlocked:
                self._lock.acquire()
            try:
                return self._invoke_blocking_command(cmd)
            except IOError, e:
                if e.errno != errno.EPIPE:
                    raise
            # The cbus_cli is not running.  Try to restart it and try again.
            self._restart()
            return self._invoke_blocking_command(cmd)
        finally:
            if unlocked:
                self._lock.release()
        pass
    def _get_network_node(self, network_path):
        assert self._lock.locked()
        name = "local"
        if network_path != "00":
            name = "n" % network_path
        if self.has_child(name):
            return self.get_child(name)
        network_node = Network()
        network_node.configure({"parent":self,
                                "name":name,
                                "network_path":network_path})
        network_node.start()
        return network_node
    def _get_app_node(self, network_node, app):
        assert self._lock.locked()
        name = "a%s" % app
        if network_node.has_child(name):
            return network_node.get_child(name)
        # Obviously an app factory based on app id, someday...
        application_node = Application()
        application_node.configure({"parent":network_node,
                                    "name":name,
                                    "app":app})
        application_node.start()
        return application_node
    def _get_group_node(self, app_node, group):
        assert self._lock.locked()
        name = "g%s" % group
        if app_node.has_child(name):
            return app_node.get_child(name)
        # Obviously an group factory based on app id, someday...
        group_node = Group()
        group_node.configure({"parent":app_node,
                              "name":name,
                              "group":group})
        group_node.start()
        return group_node
    def _get_level_node(self, group_node):
        assert self._lock.locked()
        name = "level"
        if group_node.has_child(name):
            return group_node.get_child(name)
        # Obviously a level factory based on app id, someday...
        level_node = Level()
        level_node.pm_lic_register()
        level_node.configure({"parent":group_node,
                              "name":name})
        level_node.start()
        return level_node
    def _discover(self):
        lines = self.blocking_command("D\n", False)
        self._discovery_ts = time.time()
        for line in lines:
            self._parse_discover_line(line)
        for app in self._apps:
            for group in self._groups:
                network_node = self._get_network_node("00")
                app_node = self._get_app_node(network_node, app)
                group_node = self._get_group_node(app_node, group)
                try:
                    level_node = self._get_level_node(group_node)
                except Unauthorized:
                    msglog.log(
                        'Cbus', 
                        msglog.types.WARN, 
                        'Point capacity exceeded, unable to register new point'
                    )
        return
    def discover(self):
        self._lock.acquire()
        try:
            self._discover()
        finally:
            self._lock.release()
        return
    def _extend_list_sans_ff(self, value_string, output_list):
        for value in value_string.split(","):
            value = int(value)
            if (value != 255 and value not in output_list):
                output_list.append(value)
        return
    def _parse_discover_line(self, line):
        attributes =  line.split(",", 2)
        unit = int(attributes.pop(0).split(":")[1])
        network_path = attributes.pop(0).split(":")[1]
        if attributes:
            name, values = attributes[0].split(":")
            if (name == "groups"):
                self._extend_list_sans_ff(values, self._groups)
            elif (name == "apps"):
                self._extend_list_sans_ff(values, self._apps)
        return
    def __del__(self):
        # Purely for prototyping purposes.
        self.stop()
        return
    def _should_discover(self, **options):
        # Supposedly only called if options[auto_discover] is true.
        if options.has_key('force'):
            return True
        return self._popen and self.auto_discover and not self._discovery_ts
    ##
    # Creates/Adds children (children_nodes).
    def discover_children_nodes(self, **options):
        if self._should_discover(**options):
            self.discover()
        return self.children_nodes(auto_discover=0)
    ##
    # Creates/Adds children? returns list of names (children_names).
    def discover_children_names(self, **options):
        if self._should_discover(**options):
            self.discover()
        return self.children_names(auto_discover=0)
    ##
    # May create child, returns node (get_child)
    def discover_child(self, name, **options):
        if self._should_discover(**options):
            try:
                self.discover()
            except Exception, e:
                msglog.exception()
                raise ENoSuchName(name)
        return self.get_child(name, auto_discover=0)
    ##
    # May create child,  return true/false (has_child)
    def discover_name(self, name, **options):
        if self._should_discover(**options):
            try:
                self.discover()
            except Exception, e:
                msglog.exception()
                raise ENoSuchName(name)
        return self.has_child(name, auto_discover=0)
