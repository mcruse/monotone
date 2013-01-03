"""
Copyright (C) 2011 Cisco Systems

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
#!/usr/bin/python

import sys
import time
import string
from collections import deque
from operator import itemgetter

# Need to use pysqlite2 for Megatron until we upgrade Python

megatron = 1

if megatron:
    print 'Importing pysqlite2'
    from pysqlite2 import dbapi2 as sqlite
else:
    print 'Importing sqlite3'
    from sqlite3 import dbapi2 as sqlite

from xml.sax import make_parser, handler

# Configuration database schema
# nodes table:
#     contains attrbutes of the node XML tags plus three extra fields
#     nid: database node id (table scope)
#     l, r: Values calculated from a pre modified order traversal for nested set organization data
#
# properties table:
#     contains simple name/value properties, i.e. properties in the XML file with a value attribute
#
# lists table:
#     contains the list values of properties, i.e. the values for properties without value attributes
#     are assumed to be lists
# 

schema = \
"""
pragma journal_mode=wal;
pragma foreign_keys=on;
drop table if exists lists;
drop table if exists properties;
drop table if exists nodes;
drop index if exists parent_id_index;
drop index if exists nid_index;
drop index if exists pid_index;
drop index if exists lr_index;
drop index if exists path_index;

create table nodes (
    nid integer primary key asc,
    l integer,
    r integer,
    node_id text,
    name text,
    parent_id integer,
    parent text,
    config_builder text,
    inherant text,
    module text,
    description text
);

create table properties (
    pid integer primary key asc,
    nid integer,
    name text,
    value text,
    foreign key(nid) references nodes(nid) on delete cascade
);

create table lists (
    pid integer,
    name text,
    value text,
    foreign key(pid) references properties(pid) on delete cascade
);
"""


def start(s = ''):
    global start_time
    print 'Test:    ', s
    start_time = time.time()

def end(s = ''):
    global start_time, start_text
    
    duration = time.time() - start_time
    if duration > 1:
        units = 'seconds'
    elif duration > .001:
        duration *= 1000
        units = 'milliseconds'
    else:
        duration *= 1000000
        units = 'microseconds'
    print 'Duration: %.1f %s' % (duration, units)
    print 'Result:  ', s
    print

class ConfigParser(handler.ContentHandler):

    def __init__(self, db):
        self.db = db
        self.cursor = self.db.cursor()
        self.stack = []
        self.in_var_dict = False
        self.var_stack = []
        self.path_stack = []

    def startElement(self, name, attrs):
        if name == "node":
            nodename = attrs['name']

            if nodename == '/':
                # Set the parent_id of the root node to 0, i.e no parent
                parent_id = 0
                parent = ''
            else:
                # Otherwise set the parent_id to the id on the top of the stack
                parent_id = self.stack[-1]
                parent = string.join(self.path_stack, '/')[1:]
                if parent == '':
                    parent = '/'

            # Insert the node into the nodes table
            p = (0, 0,  attrs['node_id'], nodename, parent_id,  parent, attrs['config_builder'], attrs['inherant'], attrs['module'], attrs['description'])
            query = 'insert into nodes (l, r, node_id, name, parent_id, parent, config_builder, inherant, module, description) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
            c = self.cursor.execute(query, p)
            

            # Insert into paths table for fast lookup -- Moved parent path into nodes table
            #p = (string.join(self.path_stack, '/')[1:], c.lastrowid)
            #query = 'insert into paths (path, nid) values (?, ?)'
            #c = self.cursor.execute(query, p)


            # Push the rowid of the new node on the stack and the current node name on the path stack
            self.stack.append(c.lastrowid)
            self.path_stack.append(nodename)

        # Are we inside a config section
        if len(self.var_stack):
            # If this is a property without a value attribute
            # then start processing the list of dictionaries
            # There are list tags but as they are implied I ignore them
            if self.var_stack[-1] == 'proplist':
                if name == 'dictionary':
                    self.var_stack.append('dictionary')

            # If we have found a property inside a dictionary then grap the name and value pairs
            # Note: that 'variables' are a special case. Also need to check deployed_objects, attributes etc
            if self.var_stack[-1] == 'dictionary':
                if name == 'property':
                    if attrs['name'] in ('vn', 'name'):
                        self.listentry_name = attrs['value']
                    if attrs['name'] in ('node_reference', 'value'):
                        p = (self.property_id, self.listentry_name, attrs['value'])
                        query = 'insert into lists values (?, ?, ?)'
                        self.cursor.execute(query, p)

        # Process a property within a config section
	if name == "property" and len(self.var_stack) == 0:
            if attrs.has_key('value'):
                v = attrs['value']
            else:
                self.var_stack.append('proplist')
                self.proplist_name = attrs['name']
                v = 'proplist'

            p = (self.stack[-1], attrs['name'], v)

            query = 'insert into properties (nid, name, value) values (?, ?, ?)'
            self.property_id = self.cursor.execute(query, p).lastrowid

    def endElement(self, name):
        if name == 'node':
            self.stack.pop()
            self.path_stack.pop()

        # Finish processing a dictionary entry in a proplist
        if name == 'dictionary' and self.var_stack[-1] == 'dictionary':
            self.var_stack.pop()

        # Finish processing a property within a proplist
        if name == 'property':
           if len(self.var_stack) and self.var_stack[-1] == 'proplist':
               self.var_stack.pop()               

    def startDocument(self):
        print 'Parsing xml'

    def endDocument(self):
        print 'Parsing complete'

class Config:
    def __init__(self, db_name):
        self.db = sqlite.connect(db_name)
        self.db.row_factory = sqlite.Row
        self.cursor = self.db.cursor()
        self.count = 0
        self.paths = []
        self.nodelist = []
        
    def check_db(self):
        # If the nodes tables does not exist then the length of the pragma result will be zero
        # That means that the nodes table does not exist and an import will be needed
        if len(self.cursor.execute('pragma table_info(nodes)').fetchall()) > 0:
            return 1
        else:
            return 0

    def import_xml(self, xml):
        print 'Initializing database'
        self.cursor.executescript(schema)
        parser = make_parser()
        parser.setContentHandler(ConfigParser(self.db))
        parser.parse(xml)
        print 'Building parent_id index'
        self.cursor.execute('create index parent_id_index on nodes (parent_id)')
        print 'Building nid index'
        self.cursor.execute('create index nid_index on properties (nid)')
        print 'Building pid index'
        self.cursor.execute('create index pid_index on lists (pid)')

        print 'Generating nested set data'
        self.rebuild_tree(1, 1)

        print 'Building lr index'
        self.cursor.execute('create index lr_index on nodes (l, r)')

        print "Database commit"
        self.db.commit()
        print

    def get_node(self, id, fields='*'):
        result = self.cursor.execute('select * from nodes where nid=?', (id,)).fetchone()
        return dict(result)


    def get_name(self, id):
        return str(self.get_node(id)['name'])

    def get_names(self, ids):
        t = ()
        for id in ids:
            t = t + (str(self.get_name(id)),)
        return t

    def get_parent_id(self, id):
        return self.get_node(id)['parent_id']

    def get_lr(self, id):
        n = self.get_node(id)
        return (n['l'],n['r'])

    def get_id(self, path):
        # Split the path elements discarding the empty string caused by the leading '/'
        elements = path.split('/')[1:]
   
        # Start at the root node
        id = 1
        for e in elements:
            result = self.cursor.execute('select name,nid from nodes where parent_id=? and name = ?', (id, e)).fetchone()
            # If the name field is none that the path is broken at this point
            if result == None:
                return None
            id = result['nid']
        return result['nid']

    def get_path_adjacency(self, id):
        nodepath = ''
        if id == 1:
            return '/'
        parent_id = 1
        query = 'select name,parent_id from nodes where nid=?'
        while parent_id:
            result = self.cursor.execute(query, (id,))
            name, parent_id = result.fetchone()
            if name != '/':
                nodepath = '/' + name + nodepath
            id = parent_id
        return str(nodepath)

    # Get all the children of a node
    def get_children(self, id):
        result = self.cursor.execute('select nid from nodes where parent_id=?', (id,)).fetchall()
        if len(result):
            return zip(*result)[0]
        else:
            return ()
    
    # Get all the children of a node an sort them by their priority property
    # if they have them. If the priority property is not present a default of 
    # 9999 is used.             
    def get_children_by_priority(self, id):
        d = {}
        children = self.get_children(id)
        for child in children:
            config = self.get_config(child)
            if config.has_key('priority'):
                d[child] = config['priority']
            else:
                d[child] = 9999
                
        if len(children):
            return zip(*sorted(d.items(), key=itemgetter(1)))[0]
        else:
            return ()
                    
    # DFS using database iterative search
    def dfs_adjacency(self, id, start=1):
        if start:
            self.nodelist = []
        self.nodelist.append(id)
        children = self.get_children(id)
        for child in children:
            self.dfs_adjacency(child, start=0)
        return self.nodelist

    # Get the path of a node using a nested set query
    def get_path(self, id):
        if id == 1:
            return '/'
        query = 'select parent.name from nodes as node,nodes as parent where node.l between parent.l and parent.r and node.nid=? order by parent.l'
        result = self.cursor.execute(query, (id,)).fetchall()
        return str(string.join(zip(*result)[0], '/')[1:])

    # DFS using results from modified pre-order traversal information
    def dfs(self, id):
        result = self.cursor.execute('select l,r from nodes where nid=?', (id,)).fetchone()
        l, r = result
        result = self.cursor.execute('select nid from nodes where l > ? and r < ?', (l, r)).fetchall()
        if len(result):
            return (id,) + zip(*result)[0]
        else:
            return (id,)

    # Generate a list of nodes in breadth first search order
    # This is the node configuration order used in system.py
    def bfs(self, id):
        nids = []
        q = deque((id,))
        while len(q):
            id = q.popleft()
            nids.append(id)
            q.extend(self.get_children(id))
        return nids
            
    # Add node as a child of 'parent_id'
    #
    # Need to account for case where the parent has no children yet...
    #
    def add_node(self, parent_id, config, update_lr=0):
        l, r = self.cursor.execute('select l,r from nodes where parent_id=? order by l desc limit 1', (parent_id,)).fetchone()
        if (update_lr):
            self.cursor.execute('update nodes set r=r+2 where r>?', (r,))
            self.cursor.execute('update nodes set l=l+2 where l>?', (r,))
        p = (parent_id, r+1, r+2) + config
        query = 'insert into nodes (parent_id, l, r, name, description, inherant, module, node_id) values (?, ?, ?, ?, ?, ?, ?, ?)'
        c = self.cursor.execute(query, p)

    def get_config(self, id):
        #total_start_time = time.time()
        # Get the node configuration
        query = 'select * from nodes where nid=?'
        #start_time = time.time()
        result = self.cursor.execute(query, (id,)).fetchone()
        #node_query_time = time.time() - start_time
        d = dict(result)

        # Get the properties of this node
        query = 'select * from properties where nid=?'
        #start_time = time.time()
        properties = self.cursor.execute(query, (id,)).fetchall()
        #prop_query_time = time.time() - start_time
        for prop in properties:
            name = prop['name']
            if prop['value'] == 'proplist':
                 query = 'select name,value from lists where pid=?'
                 entries =  self.cursor.execute(query, (prop['pid'],)).fetchall()
                 value = map(dict, entries)

                 # If this is a variable list then exchange keys (name, value) with (vn, node_reference)
                 # Might need to do this for other proplist style properties that don't use (name, value) keys
                 if name == 'variables':
                     tmp = []
                     for e in value:
                         tmp.append({'vn':str(e['name']), 'node_reference': str(e['value'])})
                     value = tmp
            else:
                value = str(prop['value'])

            d[name] = value

        # Convert unicode strings to str types -- Is this really necessary?
        for k in d.keys():
            if type(d[k]) == unicode: d[k] = str(d[k])

        #total_time = time.time() - total_start_time
        #print '%6d %6d %6d' % (total_time * 1000000, node_query_time * 1000000, prop_query_time * 1000000)

        return d
            
    # Traverse the tree structure using a modified pre-order traversal updating the l and r
    # values as we go. This speeds up ancestral and decendant traversals    
    def rebuild_tree(self, parent_id, left):
        right = left + 1
        query = 'select nid from nodes where parent_id=?'
        result = self.cursor.execute(query, (parent_id,)).fetchall()
        for row in result:
            right = self.rebuild_tree(row['nid'], right)
        query = 'update nodes set l=?, r=? where nid=?'
        self.cursor.execute(query, (left, right, parent_id))
        return right + 1

    def get_config_test(self):
        nids = self.dfs(1)
        start('get_config_test')
        for node in nids:
            d = self.get_config(node)
        end() 

    def test(self, xml, id):
        start('XML import and populate database'); self.import_xml(xml); end()
        start('Generate node list - DFS(adjacency list)'); nids = self.dfs_adjacency(1); end('%d nodes' % len(nids))
        start('Generate node list - DFS(nested set)'); nids = self.dfs(1); end('%d nodes' % len(nids))
        start('Generate node list - BFS(adjacency list)'); nids = self.bfs(1); end('%d nodes' % len(nids))
        start('Get node path from id (adjacency list)'); nodepath = self.get_path_adjacency(id); end(nodepath)
        start('Get node path from id (nested set)'); nodepath = self.get_path(id); end(nodepath)
        start('Get node id from path'); nid = self.get_id(nodepath); end('%d' % nid)
        start('Get configuration dictionary'); d = self.get_config(nid); end(d)
        start('Add node no lr update'); self.add_node(1, ('testnode1', 'no lr update', 'f', '/module', 't1')); end()
        start('Add node easy with lr update'); self.add_node(1, ('testnode2', 'near end of r order', 'f', '/module', 't2'), 1); end()
        start('Add node hard with lr update'); self.add_node(7, ('testnode3', 'near beginning of r order', 'f', '/module', 't3'), 1); end()
        start('Rebuild nested set data'); self.rebuild_tree(1, 1); end()

# Get the child of a node with the largest l value
"""
select name,nid,l,r from nodes where parent=1 order by l desc limit 1;
"""

# Count number of children for each row in a temp table
"""
create table temp as select id,name from nodes where desc like 'A group%'
select temp.id,temp.name,count(*) as n from temp,nodes where nodes.parent=temp.id group by temp.id order by n
"""


#cfg = Config('tron0.xml', 'broadway.sqlite')
          


