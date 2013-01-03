"""
Copyright (C) 2004 2010 2011 Cisco Systems

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
# Provides the basic interface to an usb port via an ion.
#
import time
import moab.linux.lib.usb as USB
import moab.linux.lib.process as PROC
from mpx.lib.scheduler import scheduler
from mpx.lib import msglog
from mpx.lib.node import CompositeNode
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.configure import as_boolean, as_onoff
from mpx.lib.event import EventProducerMixin, USBChangeEvent
from mpx.service.status.storage import create_partition_tree, remove_partition_tree
#
class USBNode(CompositeNode, EventProducerMixin):
    def __init__(self):
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
        return
    def configure(self, config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'debug', 0, config, as_boolean)
        return
    def configuration(self):
	config = CompositeNode.configuration(self)
        get_attribute(self, 'debug', config, as_onoff)
	return config
    # Note: update() is designed to be a public interface (called via
    #       XML-RPC), so beware when messing with it.
    def update(self, partition, hint=None):
        msglog.log('USB', msglog.types.INFO,
                   'In update with partition of %s & hint of %s.' % (partition,
                                                                     hint))
        type = 'update'
        e = USBChangeEvent(self, type)
        e.device = None
        e.partition = partition
        self.event_generate(e)
        for x in self.children_nodes():
            x.update(partition, hint)
#
class USBStorage(CompositeNode, EventProducerMixin):
    def __init__(self):
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
        self._drives = []
        self.isStarted = 0
        self.sched_id = None
        self.period = 15
        return
    #
    def configure(self, config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'debug', 0, config, as_boolean)
        return
    #
    def configuration(self):
	config = CompositeNode.configuration(self)
        get_attribute(self, 'debug', config, as_onoff)
	return config
    #
    def update(self, partition, hint=None):
        msgstr = 'In update with partition of %s and hint of %s.' % (partition,
                                                                     hint)
        msglog.log('USB_Storage', msglog.types.INFO,
                   msgstr)
        type = hint
        e = USBChangeEvent(self, type)
        e.device = None
        e.partition = partition
        self.event_generate(e)
        # Note: @fixme:  We should inform any relevant services/statues/storage
        #       nodes here, because the partitions that they represent may have
        #       been added, or gone away here.  Note also, this methodology will
        #       not catch the case when a partition has been manually
        #       dismounted.
    #
    def start( self ):
        CompositeNode.start( self )
        if not self.isStarted:
            self.isStarted = 1
            self._schedule(.15)
        else:
            raise EAlreadyRunning
    #    
    def stop( self ):
        CompositeNode.stop( self )
        if self.sched_id:
            scheduler.cancel( self.sched_id )
            self.sched_id = None
        self.isStarted = 0
    #
    def _add_services_node(self, device):
        # Find any relevant partitions and call create_partition_tree
        # as appropriate.
        msglog.log('USBStorage', msglog.types.INFO,
                   'In _add_services_node with device %s.' % device)
        # Note: @fixme, for now just call create_partition_tree for
        #       the first partition.  This is seriously broken.
        try:
            part = device + '1'
            create_partition_tree(part, '/mnt/%s' % part)
        except:
            msglog.log('USBStorage', msglog.types.WARN,
                       'Got exception trying to create_partition_tree for %s.' % device)
            msglog.exception()
    #
    def _remove_services_node(self, device):
        # Find any relevant partitions and call remove_partition_tree
        # as appropriate.
        msglog.log('USBStorage', msglog.types.INFO,
                   'In _remove_services_node with device %s.' % device)
        # Note: @fixme, for now just call remove_partition_tree for
        #       the first partition.  This is seriously broken.
        try:
            part = device + '1'
            remove_partition_tree(part)
        except:
            msglog.log('USBStorage', msglog.types.WARN,
                       'Got exception trying to remove_partition_tree for %s.' % device)
            msglog.exception()
    #
    def _add_device_node(self, device):
        cd = {'name':device, 'parent':self,
              'device':device, 'debug':self.debug}
        node = USBStorageDevice()
        node.configure(cd)
        node.start()
    #
    def _remove_device_node(self, device):
        dn = self.get_child(device)
        dn.prune()
    #
    def _add_device_event(self, device):
        e = USBChangeEvent(self, 'add')
        e.device = device
        self.event_generate(e)
    #    
    def _remove_device_event(self, device):
        e = USBChangeEvent(self, 'remove')
        e.device = device
        self.event_generate(e)  
    #
    def _do_check(self):
        try:
            return USB.scandrives(confirm=1)
        except Exception, e:
            msglog.log('USBStorage', msglog.types.WARN,
                       'Got an exception trying to scandrives.')
            msglog.exception()
            # Note: @fixme:  Probably should do some kind of test
            #       here to see if one of the drives we currently
            #       think is there, is not really "there" any more.
            #       If it isn't, we might send out some kind of
            #       ioerror event.
            return None
    #
    # Returns 1 if we should check again relatively soon, 0 otherwise.
    def _check_status(self):
        bail = 0
        # Check to see if the hotplug lock file exists.  If so, bail for now.
        hotstat = PROC.status_from_name('hotplug')
        if hotstat.state != PROC.StatusEnum.DOESNOTEXIST:
            # Looks like it exists.  Bail for now.
            bail = 1
        if not bail:
            _dstatus = self._do_check()
            if _dstatus != self._drives:
                # If it has changed, wait a couple of seconds, and
                # make sure we aren't stomping on hotplug.
                time.sleep(2)
                #
                hotstat = PROC.status_from_name('hotplug')
                if hotstat.state != PROC.StatusEnum.DOESNOTEXIST:
                    # Looks like it exists.  Bail for now.
                    bail = 1
        if bail:
            mstr =  'hotplug lock file exists.  Not checking USB status. '
            mstr += 'Got pid of %d.' % hotstat.pid
            msglog.log('USBStorage', msglog.types.WARN, mstr)
            return 1
        #
        if _dstatus and (_dstatus != self._drives):
            print 'Drive status has changed to %s.' % str(_dstatus)
            # Since drive status has changed, check for the hotplug lock file
            # again.  This should guard against the case where the kernel
            # detects the device and starts to run hotplug but this routine
            # gets in first.
            hotstat = PROC.status_from_name('hotplug')
            if hotstat.state != PROC.StatusEnum.DOESNOTEXIST:
                mstr =  'hotplug lock file exists now.  Not checking USB status. '
                mstr += 'Got pid of %d.' % hotstat.pid
                msglog.log('USBStorage', msglog.types.WARN, mstr)
                return 1
            for x in _dstatus:
                if not x in self._drives:
                    self._add_services_node(x)
                    self._add_device_node(x)
                    self._add_device_event(x)
            for x in self._drives:
                if not x in _dstatus:
                    self._remove_services_node(x)
                    self._remove_device_node(x)
                    self._remove_device_event(x)
            self._drives = _dstatus
        return 0
    #
    def _schedule( self, period = None ):
        if period == None:
            period = self.period
            retval = self._check_status()
            if retval:
                period = 2
        if self.isStarted:
            # Wake up every period seconds and check to see if we
            # need to change our status.
            self.sched_id = scheduler.seconds_from_now_do( period,
                                                           self._schedule,
                                                           None )
#
class USBStorageDevice(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        return
    #
    def configure(self, config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'debug', 0, config, as_boolean)
        set_attribute(self, 'device', None, config)
        return
    #
    def configuration(self):
	config = CompositeNode.configuration(self)
        get_attribute(self, 'debug', config, as_onoff)
        get_attribute(self, 'device', config)
	return config
#
def factory():
    return USBNode()
#
def storage():
    return USBStorage()
#
def storage_device():
    return USBStorageDevice()
