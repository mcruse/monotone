"""
Copyright (C) 2001 2002 2003 2004 2005 2006 2007 2008 2009 2010 2011 Cisco Systems

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
# Defines the base node classes and interfaces.
#

import os
import string
import types
import urllib
from cStringIO import StringIO
from mpx import properties
from mpx import componentry
from mpx.componentry import implements
from mpx.componentry import provided_by
from mpx.lib import EnumeratedValue
from mpx.lib import _singleton
from mpx.lib import msglog
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import get_attribute
from mpx.lib.configure import outstanding_attributes
from mpx.lib.configure import set_attribute
from mpx.lib.configure import as_boolean
from mpx.lib.exceptions import EAttributeError
from mpx.lib.exceptions import ECircularReference
from mpx.lib.exceptions import EConfigurationIncomplete
from mpx.lib.exceptions import EImmutable
from mpx.lib.exceptions import EInternalError
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import EMissingAttribute
from mpx.lib.exceptions import ENameInUse
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import ENoSuchNode
from mpx.lib.exceptions import ENotImplemented
from mpx.lib.exceptions import ETypeError
from mpx.lib.exceptions import EUnknownScheme
from mpx.lib.exceptions import MpxException
from mpx.lib.thread import allocate_lock
from mpx.lib.thread import get_ident
from mpx.lib.rna import HTTPTransport
from mpx.lib.rna import HTTPSTransport
from mpx.lib.rna import NodeFacade
from mpx.lib.rna import SimpleTcpTransport
from mpx.lib.rna import SimpleTextProtocol
from mpx.lib.rna import XMLRNAProtocol
from mpx.lib.rna import RNA_CLIENT_MGR
from mpx.lib.url import URL
from mpx.lib.url import ParsedURL
from mpx.lib.node.interfaces import IInspectable
from mpx.lib.node.interfaces import IConfigurableNode
from mpx.lib.node.interfaces import ICompositeNode
from mpx.lib.node.interfaces import IAliasNode
from mpx.lib.node.interfaces import IDeferred
from mpx.lib.node.interfaces import IRootNode

DEBUG = 0
UNDEFINED = object()

##
# @return True if the object is a Broadway node.
def is_node(obj):
    return hasattr(obj, 'name') and hasattr(obj, 'parent')

def is_deferred_node(obj):
    return isinstance(obj, DeferredNode)

##
# @return True if the object is a Broadway node that supports the get() method.
def is_gettable(node):
    return hasattr(node, 'get')

##
# @return True if the object is a Broadway node that supports the set() method.
def is_settable(node):
    return hasattr(node, 'set')

##
# @return True if the object is a Broadway node that supports the
#         configure() and configuration() methods.
def is_configurable(node):
    return hasattr(node, 'configure') and hasattr(node, 'configuration')

##
# @return True if the object is a Broadway node that supports the _add_child(),
#         has_child(), get_child(), children_nodes(), and children_names()
#         methods.
def is_composite(node):
    return hasattr(node, '_add_child') and hasattr(node, 'get_child')

##
# @return True if the object is a Broadway node that supports the
#         methods.
def is_runnable(node):
    return hasattr(node, 'start') and hasattr(node, 'stop')

##
# @return True if the object is a Broadway node that supports the
#         methods.
def is_running(node):
    if is_runnable(node):
        if hasattr(node, "is_running"):
            return node.is_running()
    return True

##
# @return True if the object indicates that it has a complete configuration.
# @note A configuration is considerred complete if there are no attributes
#       set to REQUIRED or the (optional) enabled attribute is false.
#       
def is_configured(node):
    if outstanding_attributes(node):
        for name in outstanding_attributes(node):
            if getattr(node, name, REQUIRED) == REQUIRED:
                return False
    return True

##
# @return True if the object has a complete configuration and it's enabled
#         attribute is set.
# @note   If a node has a valid configuration and does not have an enabled
#         attribute, it is also considered enabled (i.e. it is not disabled).
def is_enabled(node):
    # Assume objects with no "enabled" attribute are always enabled.
    return getattr(node, "enabled", True)

##
# Return the node's node_id.
# @return If the node has a node_id, then the string representation of the
#         node_id.  Otherwise, None.
# @note Node ids are currently intergers, but in the future 
def node_id(node):
    return getattr(node, "__node_id__", None)

##
# Return the node's name.
# @return If the node has a name, then the string representation of the
#         name.  Otherwise, None.
def name(node):
    return getattr(node, "name", None)

##
# Return the node's parent.
# @return If the node has a parent, then the string representation of the
#         parent.  Otherwise, None.
def parent(node):
    return getattr(node, "parent", None)

##
# ConfigurableNodes are Nodes whose name and parent is configured
# using a dictionary.  The configuration of a configurable node
# is also returned by in a dictionary.  All nodes in the Framework
# are ConfigurableNodes, therefore they all have configure and configuration
# mehtods.
#
class ConfigurableNode(object):
    implements(IConfigurableNode)
    def __init__(self):
        ##
        # All nodes have a name attribute.  You can view any node's
        # name programatically using <code>node.name</code>.
        self.name = None
        self.debug = 0
        self.enabled = 1
        ##
        # All nodes have a parent attribute.  If the node
        # is the root node, the node whose name is '/', then
        # its parent will be <code>None</code>.
        self.parent = None
        self._pruned = False
        ##
        # @note Temporary hook until NodeReferences make life much better.
        self._pruned_url = None
        # Using name-mangling because management of 
        # running state is late addition to API and 
        # many subclasses have already implemented 
        # own running-state flags and management, some 
        # of which use the name "_running," and other "running."
        self.__running = False
        super(ConfigurableNode, self).__init__()
    def callable(self, name):
        return callable(self.getattr(name))
    def hasattr(self, name):
        return hasattr(self, name)
    def getattr(self, name, default=UNDEFINED):
        value = getattr(self, name, default)
        if value is UNDEFINED:
            # Two-argument getattr used and no attribute exists.
            error = "'%s' object has no attribute '%s'"
            raise AttributeError(error % (type(self).__name__, name))
        return value
    def setattr(self, name, value):
        return setattr(self, name, value)
    def has_method(self, name):
        return callable(self.getattr(name, None))
    def provides_interface(self, interface):
        if isinstance(interface, str):
            try:
                eval(interface)
            except NameError:
                module,sep,datatype = interface.rpartition(".")
                if not module:
                    raise
                exect("import " + module)
            interface = eval(interface)
        return interface.providedBy(self)
    def get_interfaces(self, named=False):
        interfaces = list(provided_by(self))
        if named:
            items = []
            for interface in interfaces:
                items.append((interface.__module__, interface.__name__))
                interfaces = [".".join(item) for item in items]
        return interfaces
    def get_method(self, name):
        method = self.getattr(name)
        if not callable(method):
            error = "'%s' object is not callable"
            raise TypeError(error % type(method).__name__)
        return method
    ##
    # Configure a node.
    #
    # @param cd  The configuration dictionary used to configure
    #              the node.
    # @key enabled  Enable this node.  If true, then when the node's
    #               start method is called, it will start
    #               and start all of it's children.  Otherwise,
    #               don't start, enter the DISABLED state and do not
    #               progegate starting to the children.
    # @value 0;1
    # @default 1
    # @key debug  Run node in debug mode.  Some node's
    #             give additional output if they are running in
    #             debug mode.
    # @value 0;1
    # @default 0
    # @key name  The name of this node.
    # @required
    # @key parent  The url of the parent of this node.
    # @required
    #
    # @note If this node has a parent, then this node will
    #       add itself a child to that parent.
    #
    def configure(self, cd):
        previous_name = getattr(self, 'name', None)
        previous_parent = getattr(self, "parent", None)
        set_attribute(self, 'name', REQUIRED, cd)
        set_attribute(self, 'parent', REQUIRED, cd, as_internal_node)
        set_attribute(self, 'enabled', 1, cd, as_boolean)
        set_attribute(self, 'debug', 0, cd, int)
        if self.parent is not None:
            if self.parent is not previous_parent:
                self.parent._add_child(self)
                if previous_parent is not None:
                    previous_parent._remove_child(previous_name)
            elif self.name != previous_name:
                if previous_name:
                    new_name = self.name
                    self.name = previous_name
                    self.parent._rename_child(self, new_name)
                else:
                    self.parent._add_child(self)
        # Optional meta-data hooks
        if hasattr(self, '__node_id__') or cd.has_key('__node_id__'):
            set_attribute(self, '__node_id__', None, cd, str)
        if hasattr(self, '__factory__') or cd.has_key('__factory__'):
            set_attribute(self, '__factory__', None, cd, str)
    ##
    # Get the configuration parameters of the node.
    #
    # @return Dictionary containing the configuration of the node.
    #
    def configuration(self, config=None):
        if config is None:
            config = {}
        get_attribute(self, 'name', config)
        get_attribute(self, 'parent', config)
        get_attribute(self, 'enabled', config, str)
        get_attribute(self, 'debug', config, str)
        if config.has_key('parent') and config['parent']:
            get_attribute(self, 'parent', config, _get_path)
        #
        # Optional meta-data hooks
        #
        if hasattr(self, '__node_id__'):
            config['__node_id__'] = self.__node_id__
        if hasattr(self, '__factory__'):
            config['__factory__'] = self.__factory__ 
        return config
    def start(self):
        self.__running = True
        if int(properties.INIT_VERBOSITY) > 0:
            msglog.log('broadway', msglog.types.DB,
                       "start(): %r" % self.as_node_url())
    def stop(self):
        self.__running = False
    def is_running(self):
        return self.__running
    def is_pruned(self):
        return self._pruned
    ##
    # Remove this node from it's parent.
    #
    # Stop this node and then remove it from its parent's list of children.
    #
    # @param force If true (1), then failures to stop the node will be
    #              ignored and this node will be removed regardless.
    #              If false, then failures will result in an exception,
    #              with this node left in whatever state it failed in.
    # @default 0
    def prune(self, force=0):
        failmsg = "%s prune operation failed " % self    
        try:
            self.stop()
        except:
            if force:
                errormsg = failmsg + "to stop itself."
                msglog.log('broadway', msglog.types.ERR, errormsg)
                msglog.exception(prefix="handled")
            else:
                raise
        prunedurl = self.as_node_url()
        if hasattr(self.parent, "_children"):
            try:
                self.parent._remove_child(self.name)
            except:
                if force:
                    errormsg = failmsg + "to remove itself from its parent."
                    msglog.log('broadway', msglog.types.ERR, errormsg)
                    msglog.exception(prefix="handled")
                else:
                    raise
        self._pruned_url = prunedurl
        self._pruned = True
        self.parent = None
    ##
    # Return the PublicInterface of the referenced path.
    #
    # @param path Either the URL-like path to a path, or a Python reference
    #             to a path.  The path can be either absolute, or relative
    #             to self.
    # @default None Return's the Node's own PublicInterface.
    #
    # @return A Python reference to the specified node.
    # 
    # @note The PublicInterface is typically identical to the actual (aka
    #       internal) node.  In otherwords, the default behavior of the
    #       ConfigurableNode, et al classes is that as_node() is
    #       as_internal_node().  But the PublicInterface model allows a
    #       Node's implementation to differenciate between the external
    #       representation of a node and the internal implementation.  The
    #       best example of this is the Alias node.  The Alias node's
    #       PublicInterface is actually the node it for which it is an alias.
    #       The node's internal interface is the Alias instance itself, which
    #       is important for configuration, etc.
    #
    def as_node(self, path=None):
    	if path is None:
    		tonode = self
    		fromnode = None
    	else:
    		tonode = path
    		fromnode = self
    	return as_node(tonode, fromnode)
    ##
    # Return the actual instance of the referrenced node, not it's public
    # interface.
    #
    # @param path Either the URL-like path to a path, or a Python reference
    #             to a path.  The path can be either absolute, or relative
    #             to self.
    # @default None Return's the Node's own internal node.
    #
    # @see as_node For a discussion of the PublicInterface.
    #
    # @note Unless the intent is to configure an alias or some other
    #       facade, use the as_node method.
    def as_internal_node(self, path=None):
    	if path is None:
    		tonode = self
    		fromnode = None
    	else:
    		tonode = path
    		fromnode = self
        return as_internal_node(path, self)
    ##
    # Return the local URL for this node, properly encoded.
    def as_node_url(self):
        return as_node_url(self)
    ##
    # @return True (1) if this Node is enabled, i.e. if it will run when
    #         it's start method is invoked.  False (0) otherwise.
    def is_enabled(self):
        return is_enabled(self)
    ##
    # @return True (1) if this all of the Node's REQUIRED configuration
    #         attributes have been set.  False (0) otherwise.
    def is_configured(self):
        return is_configured(self)
    def has_cov(self):
        return False
    def __str__(self):
        return "%s('%s')" % (type(self).__name__, self.as_node_url())
    

##
# Package containing classes, interfaces, and functions
# associated with services.  Services are nodes that perform
# actions.  An example of typical services are the logger which enables
# both the logging and retrieving of information from log files; and
# the http_server, which listens on a port for http connections
# and enables http interaction with the MPX like file serving and
# node browsing, which are also services.
#
##
# MPX Node Interface.  All nodes in the framework
# are <code>Node</code> classes.
#
##
# CompositeNodes are ConfigurableNodes that can contain
# other ConfigurableNodes and CompositeNodes.  All Nodes in the
# Framework that can contain children nodes are CompositeNodes.
#
class CompositeNode(ConfigurableNode):
    implements(ICompositeNode)
    def __init__(self):
        super(CompositeNode, self).__init__()
    def start(self):
        self.start_children()
        super(CompositeNode, self).start()
    def stop(self):
        self.stop_children()
        super(CompositeNode, self).stop()
    def start_children(self):
        for child in self.children_nodes():
            if is_runnable(child):
                if is_enabled(child):
                    if is_configured(child):
                        try:
                            child.start()
                        except:
                            message = "%s failed to start %s."
                            message = message % (self, child)
                            msglog.log("Node", msglog.types.ERR, message)
                            msglog.exception(prefix="handled")
                    else:
                        message = ("Not starting %s because its "
                                   "configuration is incomplete")
                        message = message % child
                        missing = outstanding_attributes(child)
                        if missing:
                            details = "Missing attributes are: %s"
                            details = details % ', '.join(missing)
                        else:
                            details = "Missing attributes are unknown"
                        message = "%s.  %s." % (message, details)
                        msglog.log("broadway", msglog.types.WARN, message)
                else:
                    message = "Not starting %s because it is disabled."
                    msglog.log("broadway", msglog.types.WARN, message % child)
    def stop_children(self):
        for child in self.children_nodes():
            if is_runnable(child):
                if is_running(child):
                    try:
                        child.stop()
                    except:
                        message = "%s failed to stop %s."
                        message = message % (self, child)
                        msglog.log("Node", msglog.types.ERR, message)
                        msglog.exception(prefix="handled")
                else:
                    message = "Not stopping %s because it is not running."
                    msglog.log("broadway", msglog.types.WARN, message % child)
    ##
    # Get a list of all the children of this node.
    #
    # @return A list of Node instances that are children of this
    #         node.
    #
    def children_nodes(self, **options):
        auto_discover = options.get("auto_discover", True)
        if auto_discover and hasattr(self, 'discover_children_nodes'):
             # discover and realize the nascent nodes
            self.discover_children_nodes(**options)
        return self._get_children().values()
    ##
    # Gets a list of the names of the Nodes that are
    # children of this node..
    #
    # @return A list of the names of this node's children.
    #
    def children_names(self, **options):
        names = self._get_children().keys()
        auto_discover = options.get("auto_discover", True)
        if auto_discover and hasattr(self, 'discover_children_names'):
            names.extend(self.discover_children_names(**options))
        return names
    ##
    # Gets a list of the names of the Nodes that are
    # children AND grandchildren of this node..
    #
    # @return A list of the names of this node's (grand)children.
    #
    def descendants_names(self):
        names = []
        for child in self.children_nodes():
            names.append(urllib.unquote(child.as_node_url()))
            if is_composite(child):
                names.extend(child.descendants_names())
        return names
    ##
    # Get a child of this node by the child's
    # name..
    #
    # @param name  The name of the child to return.
    # @return The child node requested.
    # @throws KeyError If this node does not have a
    #                  with the name specified.
    #
    def get_child(self, name, **options):
        children = self._get_children()
        if children.has_key(name):
            return children[name]
        auto_discover = options.get("auto_discover", True)
        if auto_discover and hasattr(self, 'discover_child'):
            return self.discover_child(name, **options)
        raise ENoSuchName(name)        
    ##
    # Check if this node as a specific named child.
    #
    # @param name  The name of the child to check for.
    # @return 1 if the child exists, 0 otherwise.
    #
    def has_child(self, name, **options):
        try:
            child = self.get_child(name, **options)
        except ENoSuchName:
            return False
        else:
            return True
    def has_children(self):
        return bool(self._get_children())
    ##
    # Gets a dictionary of any children of this node.
    #
    # @return A dictionary of all Nodes that are children
    #         of this node.  If there aren't any, an empty
    #         dictionary is returned.
    #
    # Note:   Please don't access the _children attribute of a node any
    #         more, go through this interface.  This helps support
    #         auto-discovery of children nodes.
    #
    def _get_children(self):
        return self.getattr("_children", {})
    ##
    # Add node as a child.
    #
    # Ideally, this should only be called by this node, or the child node.
    #
    # @param node  The node to add as a child.
    #
    # Note: This method explicitly does not use _get_children()
    #       because of the strong possibility of _add_child()
    #       being indirectly called by an overriden _get_children().
    #
    def _add_child(self, node):
        if not hasattr(self, '_children'):
            self._children = {}
        child = self._children.setdefault(node.name, node)
        if child is not node:
            raise ENameInUse("<b>%s</b> exists. Please use a different name." %node.name)
        return child
    def _remove_child(self, name):
        children = self._get_children()
        if name not in children:
            raise ENoSuchName(name)
        return children.pop(name) 
    ##
    # Change the name of an existing child
    #
    # Ideally, this should only be called by this node, or the child node.
    #
    # @param node    The node of the child to rename.
    # @param newname The new name for the child node.
    #
    def _rename_child(self, node, newname):
        children = self._get_children()
        if not children.has_key(node.name):
            raise ENoSuchName(node.name)
        elif children[node.name] is not node:
            raise TypeError("child '%s' is not node %s" % (node.name, node))
        # Make sure that newname is not already in use by a different node.
        # We do this here, even though _add_child will do it too because
        # we don't want to change the state of node if we can't successfully
        # change its name.
        if children.get(newname, node) is not node:
            raise ENameInUse(newname)
        oldname = node.name
        node.name = newname
        # Could wrap add in try, 
        # except resets to oldname, 
        # else removes old name.
        self._add_child(node)
        self._remove_child(oldname)
    ##
    # Clears the node's configuration.
    #
    # @throws ENotImplemented.
    #
    def reset(self):
        raise ENotImplemented
    ##
    # Remove this node from it's parent.
    #
    # Stops self, and any running children and then removes it from
    # its parent's list of children.
    #
    # @param force If true (1), then failures to stop any node will be
    #              ignored and this node will be removed regardless.
    #              If false, then failures will result in an exception,
    #              with this node and all the children left in whatever
    #              state they are in.
    # @default 0
    def prune(self, force=0):
        failmsg = "%s prune operation failed " % self
        children = self._get_children().values()
        for child in children:
            try:
                child.prune(force)
            except:
                if force:
                    errormsg = failmsg + ("to prune child %s." % child)
                    msglog.log('broadway', msglog.types.ERR, errormsg)
                    msglog.exception(prefix="handled")
                else:
                    raise
        return super(CompositeNode, self).prune(force)

##
# Get a node from a URL.  The URL is the fully specified name
# of the node you are looking for.  A fully specified name is
# the name of each node along the path to the node you are looking
# for, with each name in the path separated by a '/'.
#
# @param path  The path to the node.
#
# @param as_internal_node  Flag indicating what
#                          type of object to return.
# @value 0  Get the public interface for the node.
# @value 1  Get the <code>Node<code> itself, not its pulbic interface.
# @default 0
#
# @param relative_to Node from which the search starts.
# @default ROOT (i.e. as_internal_node('/'))
#
# @return A reference to the requested node.
#
def from_path(path, as_internal_node=0, relative_to=None):
    if relative_to is None:
        node = ROOT
    else:
        if isinstance(relative_to, basestring):
            node = from_url(relative_to, 0, None)
        else:
            node = relative_to
    if len(path) > 1 and path.endswith('/'):
        path = path[:-1]
    parsed = ParsedURL.fromstring(path)
    if parsed.scheme:
        cd = {}
        host = parsed.hostname
        if host:
            cd['host'] = host
            port = parsed.port
            if port:
                cd['port'] = port
        if (parsed.scheme == 'mpx'
            or parsed.scheme == 'mpxao'
            or parsed.scheme == 'mpxfe'):
#            msg = "from_path: parsing mpx: %s" % path
#            msglog.log("broadway", msglog.types.INFO, msg)
            p = RNA_CLIENT_MGR.getSimpleTextProtocol(cd, parsed.scheme)
        else:
            cd['node'] = parsed.path
            # I don't like this...
            if parsed.username:
                username = parsed.username
            else:
                username = "mpxsystem"
            if parsed.password:
                password = parsed.password
            else:
                password = "EWepH8Jq"
            cd['username'] = username
            cd['password'] = password
            if parsed.scheme == 'xmlrna':
                t = HTTPTransport(**cd)
                p = XMLRNAProtocol(t)
            elif parsed.scheme == 'xmlrnas':
                t = HTTPSTransport(**cd)
                p = XMLRNAProtocol(t)
            else:
                raise EUnknownScheme(parsed.scheme)
        return NodeFacade(path, parsed.path, p)
    segments = parsed.segments()
    if not segments:
        if hasattr(node, '_public_interface'):
            node = node._public_interface()
        return node
    # Scan away...
    for index,segment in enumerate(segments):
        if segment == '':
            # Initial and double '/' are '' segments.
            node = ROOT
        elif segment == ".":
            pass
        elif segment == "..":
            if node.parent is not None:
                node = node.parent
        else:
            name = segment
            if node.has_child(name):
                node = node.get_child(name)
            else:
                # Use the path up to and including the missing segment, but not
                # beyond.
                raise ENoSuchName("%s has no child '%s'" % (node, name))
            if not as_internal_node and hasattr(node, "_public_interface"):
                node = node._public_interface()
    return node

##
# @param value  The url that is being tested.
# @return True if <code>value</code> can be resolved 
#         to a node reference.
#
def is_node_url(value):
    if not isinstance(value, basestring):
        return False
    try:
        node = as_internal_node(value)
    except:
        node = None
    return node is not None

##
# Get a node from a URL or from a reference to the node.
# If <code>value</code> is an URL, the URL needs to be the
# fully specified name of the node you are looking for.  A fully
# specified name is the name of each node along the path to the node you
# are looking for, with each name separated by a '/'.
#
# @param value  The URL of, or a reference to, the node you are looking for.
# @return A Reference to the requested node.
#
def as_node(value, relative_to=None):
    if is_node(value):
        return value
    if isinstance(value, basestring):
        return from_path(value, 0, relative_to)
    raise EInvalidValue('value', value, 'expected node reference')

##
# Get an URL from a node or a url.  If <code>value</code>
# is a URL to a node then it is returned unchanged, if it
# is a node reference its url will be returned.
#
# @param value  A node reference or URL.
# @return The URL for node <code>value<code>.
#
def as_node_url(value):
    if isinstance(value, NodeFacade):
        return value.as_node_url()
    if is_node(value):
        return _get_path(value)
    if is_node_url(value):
        return value
    if is_deferred_node(value):
        return value.get_deferred_url()
    raise EInvalidValue('value', value, 'expected node url')

##
# Get the internal representation of a node
# from it's url or node_instance.
#
# @param value  The url of or a reference to the
#               <code>Node</code> being sought.
# @return node.
#
def as_internal_node(value, relative_to=None):
    if isinstance(value, basestring):
        return from_path(value, 1, relative_to)
    return value

class _EUnresolvedNodeAttribute(AttributeError, ENoSuchNode):
    """
        Exception raised when attempting attribute lookup on DeferredNode 
        instance referring to non-existant node.  Because exception is 
        raised by __getattr__, it must be an AttributeError to be handled 
        properly by the system.
    """

class DeferredNode:
    implements(IDeferred)
    def __init__(self, node_url, relative_to=None):
        absolute_url = URL()
        if relative_to is not None:
            absolute_url.parse(as_node_url(relative_to))
            segments = node_url.split('/')
            for segment in segments:
                absolute_url.add_segment(segment)
        else:
            absolute_url.parse(node_url)
        self.__dict__['_DeferredNode__node_url'] = absolute_url.full_url()
        self.__dict__['_DeferredNode__node'] = None
        return
    def get_deferred_url(self):
        return self.__node_url
    def __getattr__(self, name):
        if self.__node is None:
            try:
                self.__dict__['_DeferredNode__node'] = as_node(self.__node_url)
            except ENoSuchName:
                pass
        if self.__node is not None:
            return getattr(self.__node, name)
        raise _EUnresolvedNodeAttribute(self.__node_url, name)
    def __setattr__(self, name, value):
        raise EImmutable(
            "DeferredNode does not allow directly changing attributes."
            )

def as_deferred_node(value, relative_to=None):
    try:
        node = as_node(value, relative_to)
    except ENoSuchName:
        node = DeferredNode(value, relative_to)
    return node

def reload_node(node):
    module = node.__class__.__module__
    statement = 'import %s' % module
    if '.' in module:
        path = module[:module.rindex('.')]
        module = module[module.rindex('.')+1:]
        statement = 'from %s import %s' % (path,module)
    exec(statement)
    reload(eval(module))
    config = node.configuration()
    if hasattr(node,'stop'):
        node.stop()
    del(node.parent._children[node.name])
    exec('new = %s.%s()' % (module,node.__class__.__name__))
    new.configure(config)
    if hasattr(new,'start'):
        new.start()
    return new

##
# Public Interface that exposes only the <code>configure</code> function.
# @fixme Soon to be deprecated!
class ConfigurableNodePublicInterface:
    ##
    # Constructor for class.
    #
    # @param node  Node whose configure function you want exposed
    #
    def __init__(self, node):
        self.node = node

    ##
    # @see ConfigurableNode#configure
    #
    def configure(self, config):
        self.node.configure(config)

    ##
    # @see ConfigurableNode#configuration
    #
    def configuration(self):
        return self.node.configuration()
##
# The generic <code>ServiceInterface</code> interface.
#
# This is the minimal public interface that a <code>ServiceNode</code>
# publishes to the outside world.
# @see mpx.lib.service for details about this class and its functions.
#
# @restriction Implementations of the <code>ServiceInterface</code>
# should only return objects that have a usable represention (i.e. they
# respond reasonably to the repr() built-in function.)
# @see repr()
# @see __repr__()
# @fixme Soon to be deprecated!
class ServiceInterface:
    ##
    # Configure the associated <code>ServiceNode</code> with
    # the supplied dictionary.
    #
    # @param cd the service's configuration dictionary.
    def configure(self, cd):
        raise ENotImplemented
    ##
    # Return the associated <code>ServiceNode</code>'s fully specified
    # configuration dictionary.
    #
    # @return a configuration dictionary.
    def configuration(self):
        raise ENotImplented
    ##
    # Start the associated service.
    #
    # @throws EAlreadyStarted if the service is already running.
    def start(self):
        raise ENotImplemented
    ##
    # Stop the service.
    #
    # @throws EAlreadyStopped if the service is not running.
    def stop(self):
        raise ENotImplemented
    ##
    # Reset the service.
    #
    def reset(self):
        raise ENotImplemented

##
# Return an anchors' priority.  The anchor might be a configuration object
# or an instanciated node, so we need to poke around the instance a bit.
def _anchor_priority(a):
    # Initialize the name to use if all else fails.
    name = None
    if hasattr(a, 'name'):
        # Get the name from the Node instance.
        name = a.name
    if hasattr(a, 'priority'):
        # This is a Node instance, use its extracted priority.
        return a.priority
    elif hasattr(a, 'get_config'):
        # This is a configuration object, look up its priority.
        config = a.get_config()
        if config.has_key('priority'):
            return config['priority']
        if hasattr(a, 'get_name'):
            name = a.get_name()
    # OK, everything else failed, use its name to determin a default priority.
    default_priorities = {'interfaces':1,
                          'services':3,
                          'aliases':2,
                          None:0x7FFFFFFF}
    try:
        return default_priorities[name]
    except:
        return default_priorities[None]

def _anchor_sort(a1,a2):
    p1 = _anchor_priority(a1)
    p2 = _anchor_priority(a2)
    return int(p1)-int(p2)

class _Root(CompositeNode):
    implements(IRootNode)
    required_attributes = ('get_child', 'has_child',
                           'children_names', 'children_nodes',
                           'name')
    def __init__(self):
        CompositeNode.__init__(self)
        self.exception = None
        self.configure({'name':'/', 'parent':None})
        return
    ##
    # Configure the root node.
    #
    # @param config  Dictionary containing configuration keys and values.
    #
    def configure(self, config):
        CompositeNode.configure(self, config)
        return
    ##
    # Get the configuration of this object.
    #
    # @return dictionary containing configuration.
    #
    def configuration(self):
        config = CompositeNode.configuration(self)
        return config
    def start(self, **kw):    
        if kw.has_key("stage"):
            stage = int(kw['stage'])
        else:
            stage = 0
        msglog.log("broadway", msglog.types.INFO,
                   "Stage %d:  starting anchors." % stage)
        self.start_children()
        # Skip CompositeNode's start() 
        # so children aren't started twice.
        ConfigurableNode.start(self)
    def stop(self, **kw):
        if kw.has_key("stage"):
            stage = int(kw['stage'])
        else:
            stage = 0
        msglog.log('broadway',msglog.types.INFO,
                   "Stage %d:  stopping anchors." % stage)
        self.stop_children()
        # Skip CompositeNode's stop() 
        # so children aren't stopped twice.
        ConfigurableNode.stop(self)
    def start_children(self):
        anchors = self.children_nodes()
        anchors.sort(_anchor_sort)
        # Start all anchors
        for index,anchor in enumerate(anchors):
            nodeurl = as_node_url(anchor)
            msglog.log('broadway', msglog.types.INFO, 
                       "Stage 6.%d:  starting %s." % (index, nodeurl))
            anchor.start()
    def stop_children(self):
        # Find the anchors and sort them according to there priority.
        anchors = self.children_nodes()
        anchors.sort(_anchor_sort)
        # Stop them in reverse order.
        anchors.reverse()
        # Stop all anchors
        for index,anchor in enumerate(anchors):
            nodeurl = as_node_url(anchor)
            msglog.log('broadway',msglog.types.INFO,
                       "Stage 6.%d:  stopping %s." % (index, nodeurl))
            anchor.stop()
    ##
    # Remove this node from it's parent.
    #
    # Stops self, and any running children and then removes it from
    # its parent's list of children.
    #
    # @param force If true (1), then failures to stop any node will be
    #              ignored and this node will be removed regardless.
    #              If false, then failures will result in an exception,
    #              with this node and all the children left in whatever
    #              state they are in.
    # @default 0
    def prune(self, force=0):
        self.__unload(force)
        return
    ##
    # Add a child <code>node</code> under root.  Children
    # must have all attributes listed in
    # <code>self.required_attributes</code>.
    #
    # @param node  Node to be added as a child.
    # @throws EmissingAttribute  If child is missing an
    #                            attribute listed in
    #                            <code>self.required_attributes.
    #
    # @throws EnameInUse  If there is already a child with
    #                     <code>node's</code> name.
    #
    def _add_child(self, node):
        for attribute in self.required_attributes:
            if not hasattr(node, attribute):
                raise EMissingAttribute, attribute
        if self.has_child(node.name):
            child = self.get_child(node.name)
            if child != node:
                raise ENameInUse, node.name
        CompositeNode._add_child(self, node)
        return
    ##
    # Clean-up prior to the unload of this ReloadableSingleton.
    def singleton_unload_hook(self):
        self.__unload(True)
        return
    ###
    # Prunes the entire node tree.
    def __unload(self, _force=1):
        # Find the anchors and sort them according to there priority.
        anchors = self.children_nodes()
        anchors.sort(_anchor_sort)
        # prune() them in reverse order.
        anchors.reverse()
        try:
            for child in anchors:
                child.prune(_force)
        except:
            if _force:
                msglog.exception()
            else:
                raise # Re-raise the original exception.
        try:
            self.stop()
        except:
            if _force:
                msglog.log('broadway', msglog.types.ERR,
                           "Failed to stop %r while pruning it from the tree."
                           % self.as_node_url())
                msglog.exception()
            else:
                raise # Re-raise the original exception.
        return

##
# The required interface that services must implement to return a reference
# to a facade via mpx.lib.node.as_node(name).
class PublicInterface:
    ##
    # Get the public interface for a <code>Node</code>
    #
    # @param node  The <code>Node</code> whose public
    #              interface is being requested.
    #
    # @return The public interface to <code>node</code>.
    #
    def _public_interface(self):
        return self

class NodeAlias(ConfigurableNode):
    """
        Base implementation for various Alias like nodes.
        
        Although this class isn't abstract, typical usage will 
        be based on a Node Alias subclass.
    """
    implements(IAliasNode)
    def __init__(self):
        self._node = None
        self.node_url = REQUIRED
        super(NodeAlias, self).__init__()
    def configure(self,config):
        set_attribute(self, 'node_url', REQUIRED, config)
        return super(NodeAlias, self).configure(config)
    def configuration(self):
        config = super(NodeAlias, self).configuration()
        get_attribute(self, 'node_url', config)
        return config
    def dereference(self, recursive=False):
        if not self.is_configured():
            message = "Unconfigured '%s' cannot be dereferenced"
            raise TypeError(message % type(self).__name__)
        target = self._noderef()
        if recursive:
            seen = set()
            while IAliasNode.providedBy(target):
                targetid = id(target)
                if targetid in seen:
                    raise ECircularReference(self.name, target.name)
                seen.add(targetid)
                target = target.dereference()
        if hasattr(target, "_public_interface"):
            target = target._public_interface()
        return target
    def _resetref(self):
        self._node = None
    def _noderef(self):
        if self._node is None:
            self._node = as_node(self.node_url)
        return self._node
    def _nodeattr(self, name):
        return getattr(self._noderef(), name)
    def __getattr__(self, name):
        if name.startswith("_") or (self.node_url is REQUIRED):
            message = "'%s' object has no attribute '%s'"
            raise AttributeError(message % (type(self).__name__, name))
        return self._nodeattr(name)
    def __str__(self):
        typename = type(self).__name__
        return "%s('%s')" % (typename, self.node_url)
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))

class Alias(NodeAlias):
    _proxied = set(['get', 'set', 'has_child', 
                    'get_child', 'children_names', 
                    '_add_child', 'children_nodes'])
    def start(self):
        return
    def stop(self):
        return
    def prune(self, force=0):
        # Remove self from the Node tree.
        try:
            if hasattr(self.parent, '_children'):
                del self.parent._children[self.name]
        except:
            if force:
                msglog.exception()
            else:
                raise # Re-raise the original exception.
        self._pruned_url = self.as_node_url()
        self.parent = None
        return
    def _public_interface(self):
        return self.dereference(True)
    def __getattr__(self,name):
        if name not in self._proxied:
            raise AttributeError(name)
        return self._nodeattr(name)

class NodeProxy(NodeAlias):
    """
        Proxy for other node.  Differs from standard 
        Alias type in the following ways:
            - Dynamically creates proxies for children of target, 
            traversal without losing alias location or perspective.
    """
    def children_names(self):
        try:
            getnames = self._nodeattr("children_names")
        except AttributeError:
            names = []
        else:
            names = getnames()
        return names
    def has_child(self, name):
        try:
            haschild = self._nodeattr("has_child")
        except AttributeError:
            exists = False
        else:
            exists = haschild(name)
        return exists
    def get_child(self, name):
        if not self.has_child(name):
            raise ENoSuchName(name)
        return self._create_child(name)
    def children_nodes(self):
        return [self.get_child(name) for name in self.children_names()]
    def _create_child(self, name, childtype=None):
        if childtype is None:
            childtype = type(self)
        elif not issubclass(childtype, NodeAlias):
            typename = type(self).__name__
            message = "'%s' object children must be 'NodeAlias' type, not: %r"
            raise TypeError(message % (typename, childtype))
        path = os.path.join(self.node_url, urllib.quote_plus(name))
        child = childtype()
        child.configure({"name": name, "parent": self, "node_url": path})
        child.start()
        return child
    def _add_child(self, node):
        pass
    def _remove_child(self, name):
        pass
    def as_node_url(self, *args, **kw):
        return super(NodeProxy, self).as_node_url()
    url = property(as_node_url)
    def nodebrowser_handler(self, nb, path, node, node_url):
        sections = nb.get_default_presentation(node, node_url)
        try:
            parsed = ParsedURL.fromstring(self.node_url)
            target = "".join([nb.request_path, parsed.path])
            if parsed.hostname:
                target = "http://%s%s" % (parsed.hostname, target)
            href = '<a href="%s" target="_blank">' % target
            configlines = StringIO(sections["node-configuration"]).readlines()
            for index,line in enumerate(configlines):
                head,sep,tail = line.strip().partition(" = ")
                if head[4:] == "node_url":
                    value = href + tail[0:-5] + "</a>"
                    tail = value + tail[-5:]
                    configlines[index] = sep.join([head, tail])
                    break
            sections["node-configuration"] = "\n".join(configlines)
        except:
            msglog.warn("Unable to create Node Browser link for target.")
            msglog.exception(prefix="handled")
        return nb.get_default_view_for(sections)
class CachingNodeProxy(NodeProxy):
    def __init__(self):
        self._children = {}
        super(CachingNodeProxy, self).__init__()
    def configure(self, config):
        nodeurl = self.node_url
        result = super(CachingNodeProxy, self).configure(config)
        if nodeurl not in (REQUIRED, self.node_url):
            self._resetref()
        return result
    def has_child(self, name):
        if name in self._children:
            exists = True
        else:
            exists = super(CachingNodeProxy, self).has_child(name)
        return exists
    def get_child(self, name):
        if name in self._children:
            return self._children[name]
        return super(CachingNodeProxy, self).get_child(name)
    def children_names(self):
        names = super(CachingNodeProxy, self).children_names()
        removed = set(self._children) - set(names)
        for name in removed:
            self.get_child(name).prune()
        return names
    def _resetref(self):
        for child in self._children.values():
            child.prune()
        super(CachingNodeProxy, self)._resetref()
    def _add_child(self, node):
        self._children[node.name] = node
    def _remove_child(self, name):
        return self._children.pop(name)

class NodeInterfaceProxy(CachingNodeProxy):
    """
        Extends Node Proxy in the following ways:
            - Inspects target node at startup and configures 
            itself as provider of all interfaces provided by target.
    """
    def __init__(self):
        self._interfaces_acquired = False
        super(NodeInterfaceProxy, self).__init__()
    def start(self):
        try:
            self._noderef()
        except:
            msglog.warn("Unable to resolve target at startup.  "
                        "Interface acquisition will be delayed.")
            msglog.exception(prefix="handled")
        return super(NodeInterfaceProxy, self).start()
    def stop(self):
        self._resetref()
        return super(NodeInterfaceProxy, self).stop()
    def _noderef(self):
        node = super(NodeInterfaceProxy, self)._noderef()
        if not self._interfaces_acquired:
            # Avoids infinite recursion caused 
            # by _acquire_interfaces() use of _noderef().
            self._interfaces_acquired = True
            try:
                self._acquire_interfaces()
            except:
                self._interfaces_acquired = False
                raise
            else:
                self._interfaces_acquired = True
        return node
    def _resetref(self):
        if self._interfaces_acquired:
            self._clear_acquired()
        self._interfaces_acquired = False
        super(NodeInterfaceProxy, self)._resetref()
    def _acquire_interfaces(self):
        try:
            get_interfaces = self._nodeattr("get_interfaces")
        except AttributeError:
            get_interfaces = IInspectable(self._node).get_interfaces
        # Force use of target node's get-interfaces.
        unprovided = []
        for interface in get_interfaces(True):
            try:
                eval(interface)
            except NameError:
                module,sep,datatype = interface.rpartition(".")
                if module:
                    exec("import " + module)
            try:
                interface = eval(interface)
            except:
                msglog.warn("Unable to apply interface: %r." % interface)
                msglog.exception(prefix="handled")
            else:
                if not interface.providedBy(self):
                    unprovided.append(interface)
        componentry.directly_provides(self, unprovided)
    def _clear_acquired(self):
        componentry.directly_provides(self, [])

##
# Node that contains only Alias references.
#
class Aliases(CompositeNode):
    def configure(self,config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'node_url', None, config)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'node_url', config)
        return config

    def start(self):
        return
    def stop(self):
        return
    def prune(self, force=0):
        # Remove self from the Node tree.
        try:
            if hasattr(self.parent, '_children'):
                del self.parent._children[self.name]
        except:
            if force:
                msglog.exception()
            else:
                raise # Re-raise the original exception.
        self._pruned_url = self.as_node_url()
        self.parent = None
        return
    def __getattr__(self,name):
        if self.node_url is not None:
            if name in ('get','set'):
                node = as_node(self.node_url)
                if hasattr(node,name):
                    return getattr(node,name)
        raise AttributeError(name)

##
# Get the path to a node in the local namespace.
#
# @param node  The node whose path is needed.
# @return String representation of node's path.
#
def _get_path(node):
    names = []
    while node.parent:
        if node is node.parent:
            raise TypeError("node parent is node")
        names.append(urllib.quote(node.name, ''))
        node = node.parent
    nodeurl = '/'
    if names:
        # Names built by append for performance, 
        # reverse order now so leaf is at end.
        names.reverse()
        nodeurl = nodeurl + '/'.join(names)
    return nodeurl

##
# Walks the children of a node in the namespace, invoking func for each visited
# node.
#
# @param node  The node whose children will be walked.
# @param func  The function to be applied to each of <code>node's</code>
#              children, each child will be passed as first param
#              to this function.
# @param args  Tuple of arguments to be passed to func after the child
#              <code>node</code>.
#
def walk(node, func, args=()):
    if hasattr(node, children_nodes):
        nodes = node.children_nodes()
        for node in nodes:
            a = [node]
            a.extend(args)
            apply(func, a)
            walk(node, func)
    return

# Create the namespace root node.
ROOT = _singleton.ReloadableSingletonFactory(_Root)
