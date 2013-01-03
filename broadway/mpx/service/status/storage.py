"""
Copyright (C) 2003 2004 2005 2010 2011 Cisco Systems

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
import statvfs
import math
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.node import CompositeNode, ConfigurableNode, as_node
from mpx.lib import msglog
from mpx.lib.event import EventProducerMixin, ResourceChangeEvent
from mpx.lib.exceptions import EAlreadyRunning, EInvalidValue

storage_root_url = '/services/status/resources/storage'

meaningful_percentage_delta = .5
meaningful_bytes_delta = 1024 * 512

##
# Node to monitor the mediator's storage.
#
class StorageNode( CompositeNode ):
    def __init__( self ):
        CompositeNode.__init__( self )
    #
    def configure( self, config_dict ):     
        CompositeNode.configure( self, config_dict )
        set_attribute( self, 'debug', 0, config_dict, int )
    #
    def configuration( self ):
        config_dict = CompositeNode.configuration( self )
        get_attribute( self, 'debug', config_dict )
        return config_dict
    #
    def tickle(self):
        for x in self.children_nodes():
            if hasattr(x, 'tickle'):
                x.tickle()
##
#
class DriveNode( CompositeNode, EventProducerMixin ):
    def __init__( self ):
        CompositeNode.__init__( self )
        EventProducerMixin.__init__( self )
        #
        self.mount_point = None
        self.debug = None
        #
        # Set old value to something which will never be valid so that
        # we always generate an event on startup.
        self.old_value = -99
    #
    def __str__(self):
        text = 'DriveNode object for mount point: %s' % str(self.mount_point)
        return text
    #
    def configure( self, config_dict ):     
        CompositeNode.configure( self, config_dict )
        set_attribute( self, 'debug', 0, config_dict, int )
        set_attribute(self, 'mount_point', '/', config_dict, str)
    #   
    def configuration( self ):
        config_dict = CompositeNode.configuration( self )
        get_attribute( self, 'debug', config_dict )
        get_attribute( self, 'mount_point', config_dict, str )
        return config_dict
    #
    def get_full( self ):
        if not os.path.exists(self.mount_point):
            return None
        return os.statvfs(self.mount_point)
    #
    def get_mount_point( self ):
        return self.mount_point
    #
    def get( self, skipCache=0 ):
        global meaningful_percentage_delta
        #
        data = self.get_full()
        if not data:
            return None
        avail = data[statvfs.F_BAVAIL] * data[statvfs.F_BSIZE]
        size = data[statvfs.F_BLOCKS] * data[statvfs.F_BSIZE]
        used = size - avail
        self.value = float(used) / float(size) * 100.0
        #
        diffvals = math.fabs(self.old_value - self.value)
        if diffvals > meaningful_percentage_delta:
            # We have a significant change here.  Let the world know!
            e = ResourceChangeEvent(self, self.old_value, self.value)
            e.available = avail
            e.used = used
            self.event_generate(e)
            self.old_value = self.value
        return self.value
    #
    def tickle( self ):
        self.get()
        # Now tickle our children in turn.
        for x in self.children_nodes():
            if hasattr(x, 'tickle'):
                x.tickle()
##
#
class DriveAttributeNode( ConfigurableNode, EventProducerMixin ):
    def __init__( self ):
        ConfigurableNode.__init__( self )
        EventProducerMixin.__init__( self )
        #
        # Set old value to something which will never be valid so that
        # we always generate an event on startup.
        self.old_value = -99
    #
    def __str__(self):
        text  = 'DriveAttributeNode object for storage '
        text += '%s and mount point: %s' % (self.name,
                                            str(self.get_mount_point()))
        return text
    #
    def configure( self, config_dict ):     
        ConfigurableNode.configure( self, config_dict )
        set_attribute( self, 'debug', 0, config_dict, int )
    #
    def configuration( self ):
        config_dict = ConfigurableNode.configuration( self )
        get_attribute( self, 'debug', config_dict )
        return config_dict
    #
    def get( self, skipCache=0 ):
        global meaningful_bytes_delta
        #
        data = self.parent.get_full()
        if not data:
            return None
        if   self.name == 'available':
            self.value = data[statvfs.F_BAVAIL] * data[statvfs.F_BSIZE]
        elif self.name == 'size':
            self.value = data[statvfs.F_BLOCKS] * data[statvfs.F_BSIZE]
        elif self.name == 'used':
            free = data[statvfs.F_BFREE] * data[statvfs.F_BSIZE]
            size = data[statvfs.F_BLOCKS] * data[statvfs.F_BSIZE]
            self.value = size - free
        else:
            raise "Child name (%s) not known" % self.name
        #
        diffvals = math.fabs(self.old_value - self.value)
        if diffvals > meaningful_bytes_delta:
            # We have a significant change here.  Let the world know!
            e = ResourceChangeEvent(self, self.old_value, self.value)
            e.name = self.name
            self.event_generate(e)
            self.old_value = self.value
        #    
        return float(self.value)
    #
    def get_mount_point( self ):
        return self.parent.get_mount_point()
    #
    def tickle( self ):
        self.get()
#    
def factory():
    return StorageNode()
#
def drive():
    return DriveNode()
#
def drive_attribute():
    return DriveAttributeNode()
#
def create_partition_tree(name, mount_point):
    global storage_root_url
    children_names = ['available',
                      'size',
                      'used',
                      ]
    msgstr =  'In create_drive_tree with name of %s ' % name
    msgstr += 'and mount_point of %s.' % mount_point
    msglog.log('Services_Storage', msglog.types.INFO,
               msgstr)
    pnode = as_node(storage_root_url)
    dict = {'name':name,
            'mount_point':mount_point,
            'debug':1,
            'parent':pnode,
            }
    drive_node = DriveNode()
    drive_node.configure(dict)
    #
    for x in children_names:
        dict = {'name':x,
                'debug':1,
                'parent':drive_node,
                }
        drive_attr_node = DriveAttributeNode()
        drive_attr_node.configure(dict)
    #
    drive_node.start()
#
def remove_partition_tree(name):
    global storage_root_url
    msgstr = 'In remove_drive_tree with name of %s.' % name
    msglog.log('Services_Storage', msglog.types.INFO,
               msgstr)
    pnode = as_node(storage_root_url)
    drive_node = pnode.get_child(name)
    drive_node.prune()
    
