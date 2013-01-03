"""
Copyright (C) 2003 2008 2010 2011 Cisco Systems

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
from mpx.service import ServiceNode
from mpx.lib import msglog
import os, string

GC_NEVER           = 0
GC_ONDELETE        = 1
GC_ASNEEDED        = 2
GC_ONFAILURE       = 3

class GarbageCollector(ServiceNode):
    def __init__(self):
        ServiceNode.__init__(self)
        self.debug = 0
        self._registered = ()
        self._did_save = 0
        self._post_configuration=0

        if self.debug: print 'Initialized _registered to [] for %s.' % self
    def singleton_unload_hook(self):
        return
    ##
    # @param config
    # @return None
    def configure(self,config):
        ServiceNode.configure(self,config)
    def configuration(self):
        if self.debug: print 'In GarbageCollector:configuration().'
        config = ServiceNode.configuration(self)
        return config
    ##
    #   starts the data manager service
    # @return None
    def start(self):
        from mpx.lib.persistent import PersistentDataObject
        
        ServiceNode.start(self)
        if self.debug: print 'Garbage Collector Starting!'

        self._data = PersistentDataObject(self,dmtype=GC_NEVER)
  
        self._data.registered = []
        self._data.load()
        
        if self.debug: print 'GC Data is %s.' % self._data
        if self.debug: print 'GC Data._reg is %s.' % self._data.registered

    ##
    #   stops the data manager service
    # @return None
    def stop(self):
        return ServiceNode.stop(self)

    ##
    # set_faillist is the hook which allows the system to inform the data
    # manager about which nodes failed to start up.  Each list item should
    # be a dictionary with the following members:
    # name - the name of the node (without parent information)
    # parent - the parent of the node (with any relevant parent information,
    #          e.g. /services/com1
    # type - what type of failure occured.  Acceptable values are
    #        load and config.
    def set_faillist(self, faillist):
        if self.debug: print 'Got faillist of %s.' % faillist
        if self.debug: print 'Got reglist of %s.' % self._registered

        old_registered = self._data.registered[:]

        # By now, everyone should have had a chance to start up.
        # @fixme (real soon now, I promise):  Use the cool new method that
        # Mark and Shane suggested to consume an event from the root node
        # when all nodes have been started as a trigger for starting
        # the garbage collection process.
        self._data.registered = list(self._registered)
  
        # OK, now process our lists and see who is naughty and who is
        # nice.
        if self.debug: print '---- Starting to Process Potential Reaping List ----'
        for regnode in old_registered:
            purge_type = regnode['type']
            filename = regnode['filename']
            nodename = regnode['nodename']
            
            # If we are never supposed to purge this data, then don't bother
            # to do any more checking
            if purge_type == GC_NEVER:
                if self.debug: print '%s: Skipping because it is GC_NEVER.' % nodename
                continue

            if self.debug: print '%s: Checking.' % nodename
            
            node_did_register = 0
            node_did_fail = 0
            node_did_fail_on_config = 0
            node_did_fail_on_load = 0
            node_did_fail_on_start = 0
            parent_did_fail = 0
            should_purge = 0

            # If this node has registered with us, then we assume that
            # it started up and is present, etc.  This might not always
            # be the correct thing to do, but for now it seems like the
            # correct enough thing to do and should keep performance
            # from becoming an issue.
            if regnode in self._registered:
                if self.debug: print '%s: Appears to be happy.' % nodename
                node_did_register = 1
            else:
                # Check to see if the node or one of it's ancestors failed
                for failnode in faillist:
                    curnode = failnode['name']
                    curpare = failnode['parent']
                    curtype = failnode['type']
                    if curpare == '/':
                        curpath = curpare + curnode
                    else:
                        curpath = curpare + '/' + curnode
                    if self.debug: print 'curpath is %s and nodename is %s.' % (curpath, nodename)
                    if nodename == curpath:
                        if self.debug: print 'We got a match, %s failed because of %s.' % (
                            nodename, curtype)
                        if curtype == 'load':
                            node_did_fail_on_load = 1
                        elif curtype == 'config':
                            node_did_fail_on_config = 1
                        else:
                            raise 'Unrecognized failure type: %s.' % curtype
                        # Don't need to check any further
                        break
                    else:
                        if self._path_is_parent(curpath, nodename):
                            if self.debug: print 'We found a parent who failed: %s.' % curpath
                            parent_did_fail = 1
                            # Don't need to check any further
                            break                        
                if node_did_fail_on_config or node_did_fail_on_load:
                    node_did_fail = 1

            # If the node didn't fail in load or config, but it didn't register either,
            # then check to see if perhaps it exists, but didn't start.  We detect this
            # by doing an as_node on it.  If this succeeds, we can check the node's state.
            # If it doesn't succeed, then we can pretty safely assume that the node
            # has been delete (or, unfortunately, is auto-discovered).  
            if not node_did_fail and not node_did_register:
                try:
                    x = as_node(nodename)
                    node_did_fail_on_start = 1
                    node_did_fail = 1
                    if self.debug: print 'We were able to instantiate node: %s.' % nodename
                except:
                    if self.debug: print 'Failed to instantiate node: %s.' % nodename
                    # The node doesn't seem to exist at all.  Let the following code
                    # draw the appropriate conclusions.
                    pass
            
            if not node_did_register:
                if self.debug: print 'node_did_fail_on_load: %d.' % node_did_fail_on_load
                if self.debug: print 'node_did_fail_on_config: %d.' % node_did_fail_on_config
                if self.debug: print 'node_did_fail_on_start: %d.' % node_did_fail_on_start
                if self.debug: print 'node_did_fail: %d.' % node_did_fail
                if self.debug: print 'parent_did_fail: %d.' % parent_did_fail
                if self.debug: print 'purge_type: %d.' % purge_type
                
                # OK, the node didn't register.  Check to see what we've
                # been told to do in this case.
                if node_did_fail and (purge_type == GC_ONFAILURE):
                    should_purge = 1

                # For now, purge even if it was a parent who failed and purge_type
                # is GC_ONFAILURE.  @fixme: We need to think about if this is what
                # we want to do or not.
                if parent_did_fail and (purge_type == GC_ONFAILURE):
                    should_purge = 1

                # If the node did not register and neither it nor a parent
                # failed to start, then we assume that it has been deleted.
                # Note: This does not seem to be correct for auto-discovered
                #       nodes, so we need a better way of detecting this case.
                if (not node_did_fail) and (not parent_did_fail) and (purge_type == GC_ONDELETE):
                    should_purge = 1

            # If the node did not register and we aren't going to purge it, then
            # save it's registration information so that if circumstances change,
            # we can consider purging it at some later date.
            if (not node_did_register) and (not should_purge):
                if self.debug: print '%s did not register, but we are registering for it.' % nodename
                self._data.registered.append(regnode)
                        
            # OK, we've figured out that we should purge this persistent
            # data.  Go ahead and do so.
            if should_purge:
                if os.access(filename, os.F_OK):
                    if self.debug: print 'We decided we should purge the following file: %s.' % filename
                    msglog.log('garbage_collector',msglog.types.INFO,
                           'Purging the following persistent data file: %s on behalf of %s.' % (filename,
                                                                                                nodename))
                    try:
                        os.remove(filename)
                    except:
                        msglog.log('garbage_collector',msglog.types.INFO,
                                   'Got exception trying to remove persistent data: %s.' % filename)
                        msglog.exception('garbage_collector')
            else:
                if self.debug: print '%s: Will SAVE the following file: %s.' % (nodename, filename)


        if self.debug: print '---- Done Processing Potential Reaping List ----'
        
        # Now, at long last, persist our own data.
        self._data.save()
        self._did_save = 1
        self._post_configuration=1

    def register(self, nodename, filename, type=None):
        # Default to GC_ONDELETE
        if type == None:
            type = GC_ONDELETE
        if self.debug: print '%s: Registered with type of %d.' % (nodename, type)
        if self._post_configuration:
            self._data.registered+=(
                {'nodename':nodename, 'filename':filename, 'type':type},
                )
        else:
            self._registered += (
                {'nodename':nodename, 'filename':filename, 'type':type},
                )

        # If we have already saved our data, but just received a new registration,
        # then save it again.
        if self._did_save:
            self._data.save()

    def _path_is_parent(self, path, node):
        # If they are the same, we aren't talking a parent/child relationship here
        if path == node:
            return 0
        strind = string.find(node, path)
        if strind == -1:
            return 0
        if strind == 0:
            return 1
        # If we got something other than -1 or 0 here, strange things are
        # happening.  Dump a message to msglog so that whatever is wrong
        # can be fixed.
        msglog.log(
            'garbage_collector',msglog.types.INFO,
            '_path_is_parent: Found %s at a weird spot in %s.' % (node,
                                                                  parent)
            )
        return 1
    ##
    # Return a tuple of dict()s describing all the registered PDOs.
    # @note DO NOT MODIFY THE DICT()s IN THE TUPLE!
    def registered_pdo_tuple(self):
        return self._registered

# Create the garbage handler singleton
from mpx.lib import ReloadableSingletonFactory
GARBAGE_COLLECTOR = ReloadableSingletonFactory(GarbageCollector)
