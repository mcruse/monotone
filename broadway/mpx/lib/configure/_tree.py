"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
# Tree node, has one parent, one-to-many children
#
class Node:
    def __init__(self):
        self.children = []
        self.num_children = 0
        self.parent = None
    
    ##
    # Set the parent for this node.
    #
    # @param parent  Parent <code>Node</code>
    #
    def set_parent(self, parent):
        self.parent = parent
    
    ##
    # Add a child <code>Node</code> to this object.
    #
    # @param child  Child <code>Node</code> object to be added.
    #
    def add_child(self, child):
        self.num_children += 1
        self.children.append(child)

    def _add_child(self, child):
        return self.add_child(child)
    
    ##
    # Get the parent <code>Node</code> of this object.
    #
    # @return Parent <code>Node</code> object.
    #
    def get_parent(self):
        return self.parent
    
    ##
    # Get a list of this object's children.
    #
    # @return List of children <code>Node</code> objects.
    #
    def get_children(self):
        return self.children

    def children_nodes(self):
        return self.get_children()
    
    ##
    # Get the number of children this objec has.
    #
    # @return Integer representing number of children.
    #
    def get_num_children(self):
        return self.num_children

##
# Class builds tree of <code>Node</code> objects
# by tracking open and close calls for each one.
#
class Tree_Builder:
    def __init__(self):
        self.root = None
        self.last_open = None
    
    ##
    # Get the root <code>Node</code> of the tree being built.
    #
    # @return <code>Node</code> object that is root of this tree.
    #         that is the <code>Node</code> created on first
    #         <code>open_node</code> call.
    #
    def get_root(self):
        return self.root
    
    ##
    # Start a new <code>Node<code>.
    #
    # @param node  <code>Node</code> to start.
    #
    def open_node(self, node):
        if not self.root:
            self.root = node
        else:
            self.last_open.add_child(node)
            node.set_parent(self.last_open)
        self.last_open = node
    
    ##
    # Close the last node opened.
    #
    # @param node  <code>Node</code> object to be closed.
    #              Defaults to None.
    #
    def close_node(self, node = None):
        # don't close it if it is the root of the tree
        if self.last_open.get_parent():
            self.last_open = self.last_open.get_parent()

##
# Class iterates through tree returning <code>Node</code>
# objects in specified order.
#
class Iterator:
    ##
    # Initialize Object.
    #
    # @param root  Optional, specifies root of
    #              tree to iterate.
    #
    # @param widith_first  Optional, defaults to 1,
    #                      set to 0 for a depth_first
    #                      iteratorion of tree.
    #
    def __init__(self, root=None, width_first = 1):
        self.width_first = width_first
        if root:
            self.set_root(root)
    
    ##
    # Set or reset the root of the tree to iterate.
    #
    # @param root  <code>Node</code> object to use as
    #              root of tree.
    #
    def set_root(self, root):
        self.index = 0
        self.children = []
        self.root = root
        if self.width_first:
            self._build_list_width_first(self.root)
        else:
            self._build_list_depth_first(self.root)
    
    ##
    # Check if there are any nodes left in tree
    # that have not been iterated through.
    #
    # @return 1 if there are any left, 0 otherwise.
    #
    def has_more(self):
        if self.index < len(self.children):
            return 1
        return 0
    
    ##
    # Get the next node in the tree.
    #
    # @return <code>Node</code> object that is next.
    #
    def get_next_node(self):
        next = self.children[self.index]
        self.index += 1
        return next
    ##
    # Remove the children of the node just returned so
    # they will not be returned as one iterates through
    # the remainder of the tree.
    #
    def remove_children(self):
        node = self.children[self.index - 1]
        children = node.get_children()
        for child in children:
            children.extend(child.get_children())
            self.children.remove(child)
    
    def _build_list_width_first(self, root):
        self.children.append(root)
        for parent in self.children:
            if hasattr(parent,'children_nodes'):
                for child in parent.children_nodes():
                    self.children.append(child)

    def _build_list_depth_first(self, root):
        self.children.append(root)
        index = 0
        for parent in self.children:
            index += 1
            count = 0
            if hasattr(parent,'children_nodes'):
                for child in parent.children_nodes():
                    self.children.insert(index + count, child)
                    count += 1
