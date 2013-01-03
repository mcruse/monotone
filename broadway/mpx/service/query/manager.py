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
import re
import fnmatch
from collections import deque
from moab.linux.lib import uptime
from mpx.lib import msglog
from mpx.lib.uuid import UUID
from mpx.lib.node import as_node
from mpx.lib.node import CompositeNode
from mpx.lib.scheduler import scheduler
from mpx.lib.entity.entity import Entity
from mpx.service.schedule.manager import ScheduleManager
from mpx.service.schedule.manager import HierarchialScheduler
from mpx.service.schedule.manager import ProxiedHierarchialScheduler
from mpx.service.network.utilities.counting import Counter
Undefined = object()
schedule_types = (ScheduleManager, 
                  HierarchialScheduler, 
                  ProxiedHierarchialScheduler)

class Query(object):
    def __init__(self, qid, iterator, **kw):
        self.qid = qid
        self.complete = False
        self.iterator = iterator
        self.returned = Counter()
        self.timeout = kw.get("timeout", 300)
        self.default_count = kw.get("count", 1000)
        self.created = self.touched = uptime.secs()
        super(Query, self).__init__()
    def id(self):
        return self.qid
    def touch(self):
        self.touched = uptime.secs()
    def since_touched(self):
        return uptime.secs() - self.touched
    def since_created(self):
        return uptime.secs() - self.created
    def expired(self):
        return self.since_touched() > self.timeout
    def next(self):
        items = self.read(1)
        if not items:
            raise StopIteration()
        return items[0]
    def read(self, count=Undefined):
        self.touch()
        if count is Undefined:
            count = self.default_count
        items = []
        complete = True
        for item in self.iterator:
            items.append(item)
            if count and len(items) == count:
                complete = False
                break
        self.complete = complete
        return items

class QueryManager(CompositeNode):
    def __init__(self, *args, **kw):
        self.queries = {}
        self.manager = None
        self.scheduled = None
        self.__default_context = None
        self.entity_manager = "/services/Entity Manager"
        super(CompositeNode, self).__init__(*args, **kw)
    def start(self):
        self.manager = as_node(self.entity_manager)
        if self.scheduled:
            self.scheduled.cancel()
        self.scheduled = scheduler.every(180, self.trim_expired)
        msglog.log('QueryManager', msglog.types.INFO, 'QueryManager Initialized')
        return super(QueryManager, self).start()
    def stop(self):
        if self.scheduled:
            self.scheduled.cancel()
        self.scheduled = None
        self.queries.clear()
        return super(QueryManager, self).stop()
    def trim_expired(self):
        trimmed = []
        for qid,query in self.queries.items():
            if query.expired():
                self.destroy_query(qid)
                trimmed.append(qid)
        return trimmed
    def find(self, args=(), **kw):
        """
            Get collection of nodes and/or entities based on 
            search criteria.
            
            Arguments provided as hash and/or keywords.  Passed 
            in hash map and keyword arguments are combined to make 
            full argument set.  Keyword argument values override 
            hash map argument values associated with same key.
            
            The following arguments are supported:
                context - optional string value specifying root 
                node or entity of search.  If Entity hierarchy is 
                configured, default context is local root entity.  
                If no entity hierarchy exists, default context is 
                root node.
                
                name - string value or pattern specifying which 
                nodes or entities should be included in the result 
                sequence.  Standard filename wildcards are supported:
                    * matches any number of any character, 
                    ? matches one of any character.
                Search compares name pattern with node names, and 
                includes matching nodes in result sequence.
                
                descendants - Boolean value indicating whether 
                nodes/entities contained by a matching node/entity 
                should also be included in the search results.  
                Default is true.  When specified and false, the 
                children of a matching node/entity are not evaluated.
                
                entities - Boolean value indicating whether 
                entity-based traversal or node-based traversal should 
                be used.  If context is an entity, default traversal 
                is entity-based; if context is not an entity, default 
                traversal is node-based.
                
                depth - integer value indicating how many levels below 
                context node/entity searching should descend.  Default 
                value is None, indicating no limit on depth; values of 
                None, NULL, false, and 0 are interpreted as no limit.
                
                ignoreCase - Boolean value indicating whether name 
                matching should be case-sensitive.  Default value is 
                false, meaning search is case-sensitive.
                
                negate - Boolean value indicating whether match status 
                should be reversed.  Default value is false.  If 
                provided and true, result set consists of those 
                nodes/entities that do *not* match the search criteria.
                
                Return value is generator that yields nodes/entities 
                of sequence.
        """
        args = dict(args)
        args.update(kw)
        depth = args.get("depth", None)
        pattern = args.get("name", "*")
        negate = args.get("negate", False)
        descendants = args.get("descendants", True)
        ignorecase = args.get("ignoreCase", False)
        context = args.get("context", self.default_context)
        if isinstance(context, str):
            context = as_node(context)
        entities = args.get("entities", isinstance(context, Entity))
        schedules = args.get("schedules", isinstance(context, schedule_types))
        if entities:
            getchildren = "get_entities"
        elif schedules:
            getchildren = "children_schedules"
        else:
            getchildren = "children_nodes"
        flags = 0
        if ignorecase:
            flags |= re.IGNORECASE
        expression = fnmatch.translate(pattern)
        regex = re.compile(expression, flags)
        items = deque([(context, 0)])
        while items:
            node,level = items.popleft()
            match = regex.match(node.name)
            if negate:
                match = not match
            if (descendants or not match) and (not depth or depth > level):
                children = getattr(node, getchildren, None)
                if children:
                    try:
                        items.extend([(child, level + 1) for child in children()])
                    except:
                        msg = 'Error in find(%s)' % getchildren
                        msglog.log(
                            'QueryManager', 
                            msglog.types.INFO, 
                            msg)
                        msglog.exception()
            if match:
                yield node
    def find_properties(self, entities, tags):
        for entity in entities:
            if hasattr(entity,'get_property_containers'):
                for container in entity.get_property_containers():
                    for property in container.get_properties(tags):
                        yield property
    def create_query(self, iterator, **kw):
        qid = str(UUID())
        self.queries[qid] = Query(qid, iterator, **kw)
        return qid
    def read_query(self, qid, count=Undefined):
        items = []
        query = self.get_query(qid)
        if query:
            items.extend(query.read(count))
            if query.complete:
                self.destroy_query(qid)
        return items
    def destroy_query(self, qid):
        removed = True
        try:
            self.queries.pop(qid)
        except KeyError:
            removed = False
        return removed
    def has_query(self, qid):
        return qid in self.queries
    def is_expired(self, qid):
        query = self.get_query(qid)
        if not query:
            return True
        return not query or query.expired()
    def as_query(self, sid):
        return self.queries[sid]
    def get_query(self, qid, default=None):
        return self.queries.get(qid, default)
    def fetch(self, args=(), **kw):
        """
            Fetch items from query.
            
            Arguments provided as hash and/or keywords.  Passed 
            in hash map and keyword arguments are combined to make 
            full argument set.  Keyword argument values override 
            hash map argument values associated with same key.
            
            The following arguments are supported:
                qid - Query ID specifying which query items should 
                be retrieved from.
                
                query - Query arguments used by "find" to create query 
                if one doesn't not already exist.
                
                count - Integer value indicating maximum number of 
                items response may include.  Default value is 1000.
                
                timeout - Number of seconds created query should 
                remain in memory without activity before being 
                garbage collected.
                
                properties - Triple purpose parameter.  Its presence 
                indicates that the results of the fetch operation 
                should be entity properties only.  Its value is 
                a hash map whose keys indicate meta-data tag names 
                and whose values are lists of values that returned 
                properties must be tagged with.  The current 
                implementation considers a match to be any property 
                for which any meta-data tag value is contained by a 
                specified meta-data tag value.
                
            Returns result object, or hash map, wtih the following 
            properties/keys: 
                qid - Query ID of query associated with result set.
                
                expired - Boolean value indicating whether query 
                associated with QID was found (based on the 
                assumption that the reason a query isn't found is 
                because it has expired).
                
                complete - Boolean value indicating whether items 
                contained by result represent all, or last, items of 
                associated query.
                
                count - Integer value indicating number of items 
                included with result.
                
                items - Array of node paths corresponding to nodes 
                yielded by find.
                
            The primary client targeted by fetch are RPC clients.  
            Because such clients cannot be given a generator object 
            directly  (RPC typically don't support streaming natively), 
            the fetch method returns result objects containing 
            subsequences of a query.  If the query result set exceeds 
            the maximum item count, clients may re-invoke fetch to read 
            the next set of items from the stream.  
            
            A callers for invocation of fetch will typically provide 
            a parameter "query" which contains the hash map arguments 
            passed to the find method to generate the result set.  The 
            result object returned by this call provides the QID of a 
            query created by fetch, up to count items from the query 
            result set, and flags indicating whether more items remain 
            in the query.
            
            Upon receipt of the result object, callers inspect the 
            "complete" flag value to determine whether more items 
            should be loaded from the query.  Until the complete flag 
            indicates all items have been read, the caller may 
            continue to invoke fetch, passing in the QID, and optional 
            count value, as the argument parameters.  
            
            Incomplete queries remain in memory for a configurable 
            number of seconds.  Invoking fetch with a QID to read 
            items from a query that no longer exists is not an error.
            The returned result object in this instance will contain 
            an empty items array, a count of 0, a complete flag of 
            true, and an expired flag indicating that the result 
            object contains no items because the query was not found.
            
            In addition to the expiration of unspent queries, all 
            queries are discarded immediately following consumption 
            of all items.  A client reading items from a query will 
            get exactly one result object with a complete flag of 
            true and no expired tag; subsequent invocations will 
            contain the expired flag indicating the query no longer 
            exists.
        """
        result = {}
        args = dict(args)
        args.update(kw)
        qid = args.get("qid")
        count = args.get("count", Undefined)
        if not qid:
            query = args.get("query")
            if not query:
                raise ValueError("fetch() requires QID or query")
            iterator = self.find(query)
            properties = args.get("properties")
            if properties:
                iterator = self.find_properties(iterator, properties)
            if count is Undefined:
                count = 1000
            result["expired"] = False
            timeout = args.get("timeout", 300)
            qid = self.create_query(iterator, timeout=timeout, count=count)
        else:
            result["expired"] = self.is_expired(qid)
        nodes = self.read_query(qid, count)
        result["qid"] = qid
        result["count"] = len(nodes)
        result["complete"] = not self.has_query(qid)
        result["items"] = [node.as_node_url() for node in nodes]
        return result
    def _get_default_context(self):
        if self.__default_context is None:
            entities = self.manager.get_entities()
            if entities:
                self.__default_context = entities[0]
            else:
                self.__default_context = as_node("/")
        return self.__default_context
    default_context = property(_get_default_context)
    
