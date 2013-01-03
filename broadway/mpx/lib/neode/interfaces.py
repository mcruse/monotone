"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
from mpx.componentry import Interface
from mpx.componentry import Attribute
from mpx.lib.interfaces import IInspectable
from mpx.componentry.security.interfaces import ISecurityContext

class INode(ISecurityContext):
    """
        Objects with these attributes make
        mpx.lib.node.is_node(object) == True
    """

    name = Attribute('Node name.')
    nodespace = Attribute('Reference to owning nodepsace object.')
    # Although ISecurityContext already specified this attr,
    #   it is respecified here because it's critical nature and
    #   additional meaning.
    url = Attribute("""
        Meant to be implemted as a property so that
        the url can be built rather than stored.
        Since INode's have a 'parent' attribute
        and a 'name,' they too have a 'url'""")

    absolute_url = Attribute("""Adds node space location to 'url'""")

    def get_nodespace():
        """
            Calling this method is the same as getting the 'nodespace'
            attribute; it returns a reference to the nodespace that
            this node is registered with.
        """

class IChildNode(INode):
    """
        Adds attributes and method associated
        with being a child of a parent to the
        INode Interface.
    """

    parent = Attribute('Reference to node parent.')

    def prune():
        """
            Remove 'self' from parent's list
            of children nodes.
        """

class IParentNode(INode):
    children = Attribute('Ditionary of child nodes')

    def add_child(object):
        """
            Add child node 'object' to chilren.

            If child's name is unique and add to children
            is succesful, this call will also add the child's
            URL to the namespace.

            Return the no
        """

    def remove_child(object):
        """
            Remove child node 'object' from children.

            Also removes child's URL from namespace.
        """

    def rename_child(child, oldname):
        """
            Manage own dictionary and also nodespace's
            dicationary to change name under which child is
            listed to child's current name attribute, from
            its previous name 'oldname'.

            Child's name attribute should reflect new name.
        """

    def create_child(factory, name):
        """
            Create child instance using factory method 'factory',
            and configure child with name 'name' and parent self.
        """

    def has_child(name):
        """
            Return 1 if this node has a child node named 'name.'
            Return 0 otherwise.
        """

    def get_child(name):
        """
            Get a child of this node that is named 'name'.
        """

    def get_index(node):
        """
            Get the index of node 'node' among
            children.
        """

    def children_nodes():
        """
            Get a list of all of this node's children.
        """

    def children_names():
        """
            Get a list of names of all this node's children.
        """

    def descendants_nodes():
        """
            Get a list of all this nodes chilren and grandchildren.
        """

    def descendants_names():
        """
            Get a list of names of all this nodes chilren and grandchildren.
        """

class IGettable(Interface):
    """
        Objects with these attributes make
        mpx.lib.node.is_gettable(object) == True
    """

    def get(async_ok=True):
        """
            Node's representing points with gettable
            values must provide this method.
        """

    def has_cov():
        """
            Return 1 if node implements COV,
            0 otherwise.
        """

    def get_returns():
        """
            Return list of types that node may
            return from 'get' call.
        """

class ISettable(Interface):
    """
        Objects with these attributes make
        mpx.lib.node.is_settable(object) == True
    """

    def set(value):
        """
            Node's representing points with settable
            values must provide this method.
        """

    def get_accepts():
        """
            Return list of return types that
            may be passed to the 'set' function.
        """

class IOverridable(Interface):
    """
        Addtional set-related methods which allow
        override type operations.
    """
    
    def override(value, seconds = None):
        """
            Base override method, provides ultimate flexibility
            via keywords; often this method will be called by
            the other, more specific, override methods.
            
            timedict of form: {'seconds': 0, 'minutes': 0, 'hours': 0}, 
            missing keys will default to 0.
        """

    def override_for(value, seconds = 0, minutes = 0, hours = 0):
        """
            Override value of point to value 'value' for time specified 
            by summing 'seconds', 'minutes', and 'hours'; correct 
            multipliers will be applied to each.
        """

    def is_overridden():
        """
            Get boolean indication of
        """

    def clear_override():
        """
            Clear override if one is currently in effect.  Return
            boolean True if point was overridden and has been cleared;
            otherwise return False to indicate that the point wasn't
            overridden and so the clear_override has had no impact.
        """
    
    def get_result(self):
        """
            Get dictionary containing current value, as well as 
            'overriden' key whose value is a boolean indication of 
            current override state.  If node is currently overriden, 
            dictionary will contain key 'override_id' which provides 
            the guid assigned to the current override.
        """

class IModifiable(Interface):
    """
        Compliments IInspector by adding
        the ability to set attributes.
    """
    def setattr(name, value, conversion = None):
        """
            Set attribute named 'name' to
            value 'value.'

            Use setattr(self, name, value)
        """

    def delattr(name):
        """
            Delete attribute named 'name' from
            'self.'

            Use delattr(self, name)
        """

class IExtendedInspectable(IInspectable):
    """
        Adds batch inspections.
    """

    def hasattrs(names):
        """
            Return list of True/False values
            according to hasattr for each name in names.
        """

    def getattrs(names, conversion = None):
        """
            Return list of attrs, applying conversion to each.
        """

    def has_methods(names):
        """
            Return list of True/False values according
            to has_method for each name in names.
        """

    def get_methods(names):
        """
            Return list of methods.
        """

class IExtendedModifiable(IModifiable):
    """
        Add batch modifiers.
    """

    def setattrs(names, values, conversion = None):
        """
            Set list of attributes named in names
            using value from values and conversion.
        """

    def delattrs(names):
        """
            Delete attributes named in names.
        """

class IConfigurable(Interface):
    """
        Objects with these attributes make
        mpx.lib.node.is_configurable(object) == True
    """

    def configure(config):
        """
            Method takes dictionary of configuration
            parameters and configures 'self' accordingly.
        """

    def configuration():
        """
            Method mirrors 'configur,' returning
            a configuration dictionary representing
            current configuration of 'self.'
        """

    def is_configured():
        """
            Return True if this node has been
            configured, False otherwise.
        """

    def reset():
        """
            Reset all of this node's configuration
            settings.
        """

class IEnableAble(Interface):
    enabled = Attribute("""
        Boolean flag indicating whether runnable object
        is currently enabled or disabled.""")

    def enable():
        """
            Enabled Runnable object.
        """

    def disable():
        """
            Disable Runnable object.
        """

    def is_enabled():
        """
            Return enabled/disabled state.
        """

class IRunnable(Interface):
    """
        Objects with these attributes make
        mpx.lib.node.is_runnable(object) == True
    """

    def start():
        """
            Method called after instantiation and configure.
        """

    def stop():
        """
            Method called prior to reconfigure, remove, etc.
        """

    def is_running():
        """
            Return True if node has been started and is currently
            running, False otherwise.
        """

class INodeSpace(Interface):
    nodetree = Attribute("""
        Copy of entire nodetree.  Retrieving this attribute
        may require considerable computing, depending upon the
        size of the node tree; usage should be reserved for
        rare and unique situations.""")

    url = Attribute("""Base URL for entire node space tree""")
    root = Attribute("""Reference to this space's root node.""")

    def as_node(path):
        """
            Return the PublicInterface of referenced path.
        """

    def as_node_collection(paths):
        """
            Return collection of referenced paths.
        """

    def as_internal_node(path):
        """
            Return the actual node of referenced path.
        """

    def as_node_url(node):
        """
            Return URL of node 'node.'
        """

    def as_node_url_collection(node):
        """
            Return collection of URLs.
        """

    def create_node(factory):
        """
            Use factory 'factory' to intantiate
            a node whose 'namespace' will be set to
            this namespace object, and return new node.
        """

    def add_node(node, url = None):
        """
            Add node 'node' to this Neodespace's nodetree using
            url 'url,' or node.url if argument is None.
        """
    def remove_node(node, url = None):
        """
            Remove node 'node' located at url 'url,' or
            node.url if 'url' is None.
        """

class IConfigurableNode(IChildNode, IInspectable, IModifiable,
                        IConfigurable, IEnableAble, IRunnable):
    """
        ConfigurableNodes are Nodes whose name and parent is configured
        using a dictionary.  The configuration of a configurable node
        is also returned by in a dictionary.  All nodes in the Framework
        are ConfigurableNodes, therefore they all have configure and configuration
        mehtods.

        Required entries in configuration dictionary are 'name', indicating
        the name of the node being configured, and 'parent', either a
        node or node url reference to the parent of this node.
    """

class ICompositeNode(IConfigurableNode, IParentNode):
    """
        Objects with these attributes make
        mpx.lib.node.is_composite(object) == True
    """

class IDeferredNode(Interface):
    """
        Used to represent non-existent children which
        will be auto-discovered.
    """

class IService(IConfigurable):
    """
        Interface matches mpx.lib.node.ServiceInterface.
    """

class IRootNode(ICompositeNode):
    """
        Root of node tree.  Has no parent.
    """

    def singleton_unload_hook():
        """
            Cleanup prior to unload of this ReloadableSingleton.
        """

class IAlias(IConfigurableNode):
    """
        Marker Interface.
    """

class IAliases(ICompositeNode):
    """
        Marker Interface.
    """
