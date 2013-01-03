"""
Copyright (C) 2001 2002 2003 2007 2009 2010 2011 Cisco Systems

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
# @todo Semaphore access to the __system_dict.
# @todo Define what a shut-down request is, and/or improve the terminology.
# @fixme Rename _system.py
# @fixme Add configuration function(s)?
from mpx import properties
from moab.linux.lib import process

import mpx.lib
from mpx.lib import msglog
from mpx.lib.configure import parse_xml, Iterator
from mpx.lib import pause
from mpx.lib.node import as_node_url, as_internal_node
from mpx.lib.exceptions import EAlreadyRunning

import os
import gc
import sys
import time

# Conditionally imported 
if os.path.exists('/home/mpxadmin/.db_config'):
    from mpx.lib.configure import db_config

configuration_file=None

__system_dict = {
    'run_func':None,
    'should_run':1,
    'exit_status':None,
    'run_thread':None
}

##
# Read an XML configuration file and configure the system.
#
# @param filename  Name of the XML file containing
#                  configuration information for
#                  this system.
# @default '/var/mpx/config/broadway.xml'
# @fixme need to handle error better
# @return The root node of this mpx.
#
def configure(filename=properties.CONFIGURATION_FILE):
    try:
        root = _configure(filename)
    except Exception, e:
        import traceback
        traceback.print_exc()
        root = as_internal_node('/')
        root.exception = e
        msglog.exception()
    else:
        msglog.log('broadway',msglog.types.INFO,
                   'Configuration complete.')
    return root

# @fixme clean up by providing an mpx.lib.node.priority_sort
from mpx.lib.node import _anchor_sort as _priority_sort



# Configure the framework from an sqlite database
# This method is called by _configure() if it finds the file .db_configure in ~mpxadmin
# If the database is not populated, the existing /var/lib/config/broadway.xml will be imported
# To force an import just delete /var/lib/config/broadway.sqlite
def _configure_from_db(filename, faillist):
    # Connect to the configuration database.
    msglog.log('broadway',msglog.types.INFO, 'Stage 1.0:  Connecting to database.')
    cfg = db_config.Config('/var/mpx/config/broadway.sqlite')

    # Check if we need to import the xml data
    if cfg.check_db() == 0:
        msglog.log('broadway',msglog.types.INFO, 'Stage 1.1:  Database is not populated. Importing from %s' % filename)
        start = time.time()
        cfg.import_xml(filename)
        duration = time.time() - start
        msglog.log('broadway',msglog.types.INFO, 'Stage 1.2:  Database XML import complete in %d seconds' % (duration, ))

    # configure the root node.
    msglog.log('broadway',msglog.types.INFO, 'Stage 2:  Configuring the root node.')

    # Get the path of the root node. Is it ever going to be anything other than '/'?
    node = mpx.lib.node.from_path(cfg.get_path(1))
    
    # Get the configuration for the root node and configure it
    c = cfg.get_config(1)
    node.configure(c)

    # Get the children of the root node sorted by their priority property.
    # This is the order that these subtrees will be configured
    anchors = cfg.get_children_by_priority(1)

    msglog.log('broadway',msglog.types.INFO, 'Stage 3:  Configuring anchors.')

    n = 0
    for a in anchors:
        n += 1
        msglog.log('broadway',msglog.types.INFO, "Stage 3.%d:  Configuring %r." % (n, cfg.get_path(a)))

        # Iterate through the nodes in breadth first order
        # Can we use depth first? It would be much faster.
        node_id_list = cfg.bfs(a)

        # Main configuration loop for each of the anchors
        # Need to handle the exceptions that the original code uses...
        # In particular, we need to continue with the next node even if
        # the current node fails for some reason.
        for nid in node_id_list:
            print '**** configuring', cfg.get_name(nid)
            config = cfg.get_config(nid)

            # Try to load the node
            try:
                node = _load(config)
            except Exception, e:
                msg = 'Failed to create node described by %r' % cd
                faillist.append({'name':cd['name'],'parent':cd['parent'], 'type':'load'})

            # Try to configure the node
            try:                          
                node.configure(config)
            except Exception, e:
                msg = 'Failed to configure node %r with %r' % ((config.get_url(), cd))
                faillist.append({'name':cd['name'],'parent':cd['parent'], 'type':'config'})

def _configure_file(filename, faillist):
    msglog.log('broadway',msglog.types.INFO,
               'Stage 1:  Parsing configuration file.')
    root = parse_xml(filename)
    # configure the root node.
    msglog.log('broadway',msglog.types.INFO,
               'Stage 2:  Configuring the root node.')
    node = mpx.lib.node.from_path(root.get_url())
    node.configure(root.get_config())

    anchors = []
    # Sort the namespace anchors according to their priority.
    for a in root.children:
        anchors.append(a)
    anchors.sort(_priority_sort)
    msglog.log('broadway',msglog.types.INFO,
               'Stage 3:  Configuring anchors.')
    n = 0
    for a in anchors:
        n += 1
        msglog.log('broadway',msglog.types.INFO,
                   "Stage 3.%d:  Configuring %r." % (n, a.get_url()))
        ai = Iterator(a)
        # The while, try, while construct minimizes constructing try/except
        # blocks which is an expensive operation.
        while ai is not None and ai.has_more():
            config = a
            state = 'none'
            try:
                while ai.has_more():
                    previous_config = config
                    state = 'lookup'
                    config = ai.get_next_node()
                    state = 'decode'
                    cd = config.get_config()
                    cd['name'] = cd['name'].strip()
                    state = 'load'
                    node = _load(cd)
                    state = 'configure'
                    node.configure(cd)
                    state = 'next'
            except Exception, e:
                # @fixme Add children, partial configure (name and parent).
                msg = ''
                if state == 'lookup':
                    msg = '%s%r%s' % (
                        'Internal failure fetching the node after ',
                        previous_config.get_url(),
                        ' in the configuration.  Aborting configuration.')
                    # We're toast, give up.
                    ai = None
                elif state == 'decode':
                    msg = (
                        'Internal failure decoding %r\'s configuration data.' %
                        config.get_url()
                        )
                elif state == 'load':
                    msg = 'Failed to create node described by %r' % cd
                    faillist.append({'name':cd['name'],'parent':cd['parent'],
                                     'type':'load'})
                elif state == 'configure':
                    msg = 'Failed to configure node %r with %r' % (
                        (config.get_url(), cd))
                    faillist.append({'name':cd['name'],'parent':cd['parent'],
                                     'type':'config'})
                else:
                    msg = 'Internal failure in %r state' % state
                msglog.log('broadway', msglog.types.ERR, msg)
                msglog.exception(msglog.types.ERR)
                if ai is not None:
                    ai.remove_children()
                    msglog.log('broadway', msglog.types.WARN,
                               'Unable to create/configure node %s, %s' %
                               (config.get_url(), 'skipping children'))
                    
##
# Inform the Garbage Collector of any nodes which had trouble starting up.
def _inform_garbage_collector(list):
    try:
        gc = as_internal_node('/services/garbage_collector')
        gc.set_faillist(list)
    except:
        msglog.exception(msglog.types.INFO)
    return

# if hardware is a megatron, open link to coprocessor
megatron = None
if properties.HARDWARE_CODENAME == "Megatron":
    print 'Megatron platform:  Start coprocessor link'
    from moab.linux.lib import megatron

def _configure(filename=properties.CONFIGURATION_FILE):
    faillist = []
    try:
        if megatron:
            megatron.setConfiguring()
        
        if os.path.exists('/home/mpxadmin/.db_config'):
            #from mpx.lib.configure import db_config
            _configure_from_db(filename, faillist)
        else:
            _configure_file(filename, faillist)
    except:
        print '***** Exception during  _configure_file', sys.exc_info()
        msglog.exception(msglog.types.ERR)

    # Ensure that the system has the minimum functional requirements.
    print '*** Performing minimal configuration ***'
    ensure_minimal_configuration()

    configuration_file = filename
    root = mpx.lib.node.as_internal_node('/')

    # Start all nodes, top down, breadth first.
    if megatron:
        megatron.setStarting()
    root.start(stage=6)

    # Inform the garbage_collector of any nodes which failed
    _inform_garbage_collector(faillist)
    
    if megatron:
        megatron.setRunning()
    return root

##
# Indicates whether the framework is currently 'running.'
#
# The framework is considerred running if one thread is currently waiting
# for one of the framework's run functions to complete.
#
# @todo Implement handling shut-down requests.
# @return True (1) if the framework is running, false (0) otherwise.
def is_running():
    # Check this process.
    if (__system_dict['run_func'] != None):
        return 1
    # Check for another process.
    if (process.status_from_name('broadway').state !=
        process.StatusEnum.DOESNOTEXIST):
        return 1
    return 0
##
# Indicates whether the framework should be running.
#
# The framework should be running if it has not received a shut-down
# request.
#
# @todo Implement handling shut-down requests.
# @return True (1) if the should be running, false (0) otherwise.
def should_run():
    return __system_dict['should_run']
##
# exit(): Call this function to cause the main framework loop to fall through
# and terminate within 1 loop wait period (currently 1 sec).
#
def exit():
    __system_dict['should_run'] = 0

def _load(cd, verbosity=properties.INIT_VERBOSITY):
    verbosity = int(verbosity)
    path = cd['parent']
    if path[-1] != '/':
        path = path + '/'
    path = path + cd['name']
    if verbosity > 0:
        msg = 'Looking up node: ' + str(path)
        msglog.log('broadway',msglog.types.INFO,msg)
    if mpx.lib.node.is_node_url(path):
        node = mpx.lib.node.from_path(path, 1)
    else:
        if verbosity > 0:
            msg = 'Creating node: ' + str(path)
            msglog.log('broadway',msglog.types.INFO,msg)
        node = mpx.lib.factory(cd['module'])
        if cd.has_key('node_id'):
            # Override the 'default' node id.
            node.__node_id__ = cd['node_id']
        else:
            # If there is no __node_id__, add the factory.
            # This doesn't make sense here, in 1.4 all this
            # moves into mpx.lib.factory().
            node.__factory__ = cd['module']
    if verbosity > 0:
        # Don't log actual passwords.
        if cd.has_key('password'):
            _cd  = cd.copy()
            _cd['password'] = '*****'
        else:
            _cd = cd
        msg = 'Configuring node %s:\n%r' % (path,_cd)  
        msglog.log('broadway',msglog.types.INFO,msg)
    return node

# @fixme Log a different message for standalone support
# @fixme Call a wrapper to _load, some may have additional logic.
# @fixme At a minimum, reconfigure anything that is no CONDIFURED.
_MINIMAL_STANDALONE_MAP = {
    '/interfaces':(_load, ({'module':'mpx.ion.host.unknown.factory',
                            'parent':'/',
                            'name':'interfaces'},)),
    '/services':(_load, ({'module':'mpx.service.factory',
                          'parent':'/',
                          'name':'services'},)),
    '/aliases':(_load, ({'module':'mpx.service.aliases.factory',
                         'parent':'/',
                         'name':'aliases'},)),
    '/services/time':(_load, ({'module':'mpx.service.time.Time',
                               'parent':'/services',
                               'name':'time'},)),
    '/services/session_manager':(
        _load, ({'module':'mpx.service.session.SessionManager',
                 'parent':'/services',
                 'name':'session_manager'},)),
    '/services/network':(
        _load, ({'module':'mpx.service.network.factory',
                 'parent':'/services',
                 'name':'network'},)),
    # @fixme disable rna and https/xml/...
    '/services/network/rna':(
        _load, ({'module':'mpx.service.network.rna.factory',
                 'parent':'/services/network',
                 'name':'rna',
                 'enabled':1},)),
    '/services/network/rna/configuration':(
        _load, ({'module':'mpx.service.configuration.factory',
                 'parent':'/services/network/rna',
                 'name':'configuration',
                 'enabled':1},)),
    '/services/alarms':(
        _load, ({'module':'mpx.lib.node.CompositeNode',
                 'parent':'/services',
                 'name':'alarms',
                 'enabled':1},)),
    '/services/status':(
        _load, ({'module':'mpx.service.status.factory',
                 'parent':'/services',
                 'name':'status',
                 'enabled':1},)),
    # @fixme Add /services/network/[rna|http?/xmlrpc/rna]...
    }

def ensure_minimal_configuration():
    msglog.log('broadway',msglog.types.INFO,
               'Stage 4:  Ensuring minimal functional configuration.')
    map = _MINIMAL_STANDALONE_MAP.copy()
    while map:
        processed = 0
        for url, action in map.items():
            load_function = action[0]	# The function to load the node.
            args = action[1]		# The arguments to the load function.
            cd = args[0]		# The first argument must be a valid
                                        # configuration dictionary.
            if mpx.lib.node.is_node_url(cd['parent']):
                if not mpx.lib.node.is_node_url(url):
                    # The parent exists, so we can create the node.
                    node = apply(load_function, args)
                    node.configure(cd)
                del map[url]
                processed += 1
        if processed == 0:
            raise '@fixme Raise a real minimal ensure failure due to ...'
    msglog.log('broadway',msglog.types.INFO,
               'Stage 5:  Configuration complete.')
    return

##
# Helper function that provides the minimal configuration for a system
# without a valid configuration.
#
# @fixme Start the configuration service, as soon as it exists.
# @depricate
# @fixme Move to the MINIMAL_..._MAP
def __create_minimal_configuration(msglog_type):
    msglog.log('broadway', msglog_type,
               'Using the minimal framework configuration.')
    # Eliminate bad node tree so that name clashes don't occur.
    root = mpx.lib.node.from_path('/')
    root._children = {}
    root.configure({'name':'/'})
    # Start services and ion tree.
    host.start()
    service_node.start()

##
# Read an xml configuration, configure the system and enter the run-loop.
#
# This function does not exit until the Broadway framework exits.
#
# @param filename  Name of an xml file containing configuration information for
#                  this system.  Regarless of the configuration, a minimal
#                  framwork is instiated that includes the following nodes:
# <code>
#     /interfaces
#     /interfaces/eth0
#     /interfaces
#     /services
#     /services/logger/msglog
#     /services/logger/msglog/exporters
#     /services/configuration
#     /services/network
#     /services/network/rna (native RNA disabled)
#     /services/network/rna/configuration
#     /services/network/http_server/xmlrpc_handler/rna_xmlrpc_handler
#     /services/network/https_server/xmlrpc_handler/rna_xmlrpc_handler
#     /aliases
# </code>
#                  This behavior ensures that the configuration tool can
#                  connect to the framework to configure it.
# @default '/var/mpx/config/broadway.xml'
# @param interactive_debug If this is set to true, then the function exits
#                          instead of enterring the normal wait state.  This
#                          is only intended for debugging purposes.
# #default false
#
# @return A Broadway exit status object.
# @note If the filename does not exist, then an error is logged and the
#       framework is configured as if the filename where None.
# @note If this function exits due to an exception, the exception is returned
#       in the Broadway exit status and the uncaught exception is logged to
#       the msglog.
# @note If this function is called by a thread that is not the 'main' thread,
#       then it is the callers responsibility to ensure that the main thread
#       does not exit until this function returns.
# @exception EAlreadyRunning Raised if the framwork is running in another
#            thread.
# @fixme Define and return Broadway exit status objects. 
# @fixme Define EAlready running.
# @fixme Semaphore is_running check.
def run(filename=None, interactive_debug=0):
    if is_running():
        raise EAlreadyRunning
    __system_dict['run_func'] = run
    try:
        process.register_named_process('broadway', os.getpid())
        # clear out any shared memory used by the framework nodes,
        # and C processes eg, C event router and/or C statitics
        if os.path.exists('/usr/bin/shmrm'):
            os.system('/usr/bin/shmrm | /usr/bin/logger -t shmrm')
        
        ## if configuration file not specified, use file from properties
        if filename == None:
            filename = properties.CONFIGURATION_FILE
        configure(filename)
        gc.collect()
        if not interactive_debug:
            # The main process enters a 'do nothing' loop.  It's an easy way
            # to keep the main thread safely active.
            while should_run():
                pause(1)
    except Exception, e:
        msglog.exception()
    except:
        msglog.exception()
    __system_dict['run_func'] = None
    return __system_dict['exit_status']

