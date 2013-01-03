"""
Copyright (C) 2010 2011 Cisco Systems

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
# Interfaces and simple classes that describe the optional
# GetMultiple interface for Node's.

class GetMultipleInterface:
    ##
    # @param nodes The list of "descendant" nodes (references or urls)
    #              to get.
    # @param keywords Optional keywords that the invoker uses to "tune"
    #                 the request.
    # @key look_ahead True indicates that the returned MultipleGetMap
    #                 should include additional nodes not in the
    #                 request, but essentially "free" for the
    #                 consumer.  False indicates that the resulting
    #                 MultipleGetMap should only include nodes
    #                 specifically requested for sorting.
    # return A MultipleGetMap describing the most efficient "batches"
    #        for get_multiple() invocations on the same node.
    #
    # @note "Self" is a descendant of itself in the context of this
    #       method.
    def sort_multiple(self, nodes, **keywords):
        raise EAbstract
    ##
    # @param nodes A single MultipleGetBatch, describing list of
    #              "descendant" nodes (references or urls) to get.
    # @return The list of values "read" in the same order as requested.
    #         Individual failures are reported as values that are
    #         exceptions.  Where the failure included a protocol layer
    #         message, the exception should provide the protocol
    #         specific representation as well.
    #
    # @note It is assumed that the invoker of this method uses
    #       'sort_multiple()' (once) to determine valid, efficient,
    #       "batches".  The logic of a get_multiple should be as
    #       stream-lined as possible.  No need to protect naive 
    #       invokers.
    #
    # @note "Self" is a descendant of itself in the context of this
    #       method.
    #
    # @note Any node that is not a descendant, or that can not
    #       participate in the multiple get should be an individual
    #       failure, as noted above.
    #
    # @note This method is always *on demand*, never cached.  The
    #       "Subscription Manager", using this, and other evolving
    #       hints and interfaces should become the "Central Point
    #       Cache".
    def get_multiple(self, nodes):
        raise EAbstract

##
# Object that describes the most efficient access methods for the
# (subset of) descendants of a node.
#
# @key 'batches' A list of MultipleGetBatch objects.
# @key 'individuals' A list of SingleGet objects.
# @key 'rejects' A list of nodes that where not known to, or appropriate
#                for the target node's sort_multiple() method.
class MultipleGetMap(dict):
    pass

##
# Object that describes the most efficient access of a single "batch"
# a node's descendants.
#
# @key 'nodes' A list of node references and/or node urls.
# @key 'ttl' A float that is a reasonable "time-to-live" for the entire batch,
#            in seconds.
class MultipleGetBatch(dict):
    pass

##
# Object that describes the most efficient access of a single
# node's descendant.
#
# @key node A node references or node url.
# @key 'ttl' A float that is a reasonable "time-to-live" for the entire batch,
#            in seconds.
class SingleGet(dict):
    pass
