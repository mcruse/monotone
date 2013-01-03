"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
import exceptions

##############################################################################
#
# class ECycleDetected
#
# Exception to report cyclic graph.
#
##############################################################################
class ECycleDetected( exceptions.Exception ):
    def __init__( self, cycle ):
        self.cycle = cycle
        
    def __str__( self ):
        return "Cycle detected in directed graph: %s" % repr( self.cycle )


##############################################################################
#
# class EMissingVertex
#
# Exception to report an incomplete graph definition.
#
##############################################################################
class EMissingVertex( exceptions.Exception ):
    def __init__( self, vname, referenced_by_v ):
        self.vname = vname
        self.referenced_by_v = referenced_by_v
        
    def __str__( self ):
        return "Missing vertex '%s' referenced by '%s'" % (self.vname, self.referenced_by_v.name)


class Edge:
    def __init__( self, node_name ):
        self.node_name = node_name
        
    def __str__( self ):
        return self.node_name
        

class Vertex:
    def __init__( self, name, edges = None ):
        if edges is None:
             edges = None
        self.name = name
        self.edges = edges
        self.touched = 0
        
    def __str__( self ):
        s = "Vertex( '%s': [" % self.name
        for e in self.edges:
            s += " '%s' " % str( e )
        s += " ] )"
        return s
    
    def reset( self ):
        self.touched = 0
        
    def touch( self ):
        self.touched = 1
        
    def is_touched( self ):
        return self.touched


class DirectedGraph:
    def __init__( self ):
        self.vertices = {}
        self.path = None
        self.sorted_names = None
        
    def __str__( self ):
        s = "<<\n"
        for vname in self.vertices.keys():
            s += "%s\n" % str( self.vertices[vname] )
        s += ">>"
        return s

    def add_vertex( self, v ):
        self.vertices[v.name] = v
    
    def has_vertex( self, name ):
        return name in self.vertices
    
    def _visit( self, v ):
        v.touch()
        self.path.append( v.name )
        
        for vname in v.edges:
            if self.vertices.has_key( vname ):
                nextv = self.vertices[vname]
            else:
                raise EMissingVertex( vname, v )
            if nextv.name in self.path:
                cycle = self.path[self.path.index(vname):]
                cycle.append( nextv.name )
                raise ECycleDetected( cycle )
            elif not nextv.is_touched(): 
                self._visit( nextv )

        self.sorted_names.append( v.name )
        self.path.pop()
    
    def sort( self ):
        self.path = []
        self.sorted_names = []
        
        for vname in self.vertices.keys():
            self.vertices[vname].reset()
            
        for vname in self.vertices.keys():
            v = self.vertices[vname]
            if not v.is_touched():
                self._visit( v )

        return self.sorted_names
    
    def get_vertice_names( self ):
        return self.vertices.keys()
    

##
# Test routine executed if this module is run as main.
##
if __name__ == "__main__":
    dag = DirectedGraph()
    #
    # Cyclic graph
    #
    dag.add_vertex( Vertex( 'A' , ['F', 'B', 'G'] ) )
    dag.add_vertex( Vertex( 'B' ) )
    dag.add_vertex( Vertex( 'C' , ['A'] ) )
    dag.add_vertex( Vertex( 'D' , ['F'] ) )
    dag.add_vertex( Vertex( 'E' , ['D'] ) )
    dag.add_vertex( Vertex( 'F' , ['E'] ) )
    dag.add_vertex( Vertex( 'G' , ['C', 'E', 'J'] ) )
    dag.add_vertex( Vertex( 'H' , ['I', 'G'] ) )
    dag.add_vertex( Vertex( 'I' , ['H'] ) )
    dag.add_vertex( Vertex( 'J' , ['L', 'M', 'K'] ) )
    dag.add_vertex( Vertex( 'K' ) )
    dag.add_vertex( Vertex( 'L' , ['M', 'G'] ) )
    dag.add_vertex( Vertex( 'M' , ['L'] ) )
    
    try:
        print "\n**** TEST 1: Expect failure  ****\n", str( dag ), dag.sort()
    except ECycleDetected, e:
        print str( e )
        
    #
    # Acylic graph
    #
    dag = DirectedGraph()
    
    dag.add_vertex( Vertex( 'A' , ['B', 'C', 'F'] ) )
    dag.add_vertex( Vertex( 'B' ) )
    dag.add_vertex( Vertex( 'C' ) )
    dag.add_vertex( Vertex( 'D' ) )
    dag.add_vertex( Vertex( 'E' , ['D'] ) )
    dag.add_vertex( Vertex( 'F' , ['D', 'E'] ) )
    dag.add_vertex( Vertex( 'G' , ['C', 'E', 'H'] ) )
    dag.add_vertex( Vertex( 'H' , ['I'] ) )
    dag.add_vertex( Vertex( 'I'  ) )
    dag.add_vertex( Vertex( 'J' , ['L', 'M', 'K'] ) )
    dag.add_vertex( Vertex( 'K' ) )
    dag.add_vertex( Vertex( 'L' , ['M'] ) )
    dag.add_vertex( Vertex( 'M' ) )
    
    try:
        print "\n**** TEST 2: Expect success ****\n", str( dag ), dag.sort()
    except ECycleDetected, e:
        print str( e )
    
