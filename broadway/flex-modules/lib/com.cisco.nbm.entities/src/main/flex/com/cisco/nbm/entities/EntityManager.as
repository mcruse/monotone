package com.cisco.nbm.entities
{
	import com.cisco.cisco_internal;
	import com.cisco.nbm.xmlrpc.v2.MediatorNode;
	import com.cisco.nbm.xmlrpc.v2.MediatorNodeCall;
	
	import flash.events.EventDispatcher;
	import flash.events.TimerEvent;
	import flash.utils.Timer;
	
	import mx.collections.ArrayCollection;
	import mx.collections.Sort;
	import mx.collections.SortField;
	import mx.logging.ILogger;
	import mx.logging.Log;
	use namespace cisco_internal;

	public class EntityManager extends EventDispatcher implements IEntityManager
	{
		private var _entities:ArrayCollection /* of IEntity */ = new ArrayCollection();

		private var cachedNames:Object = {};

		[Bindable]
		public var cachedCollection:ArrayCollection = new ArrayCollection();

		private var loaded:Boolean = false;

		private var _node:MediatorNode;

		private var logger:ILogger = Log.getLogger("cisco.nbm.entities.EntityManager");

		private var polling:Boolean = false;

		private var pollID:String;

		private var pollTimer:Timer;

		private var polledAll:Boolean = false;

		private var entityPresence:Object = {};

		public function EntityManager(node:MediatorNode)
		{
			_node = node;

			setSort();
		}

		private function setSort():void
		{
			var sort:Sort = new Sort();
			sort.fields = [ new SortField("label", true) ];

			_entities.sort = sort;
			_entities.refresh();
		}

		/**
		 * Creates a polling call for entity status
		 */
		public function startPoll():void
		{
			logger.debug("create_polled");
			if (polling || pollID != null)
			{
				logger.warn("poll already created");
				return;
			}

			var call:MediatorNodeCall = _node.execute("create_polled", null);
			call.addCallback(handleCreatePolledResult, handleCreatePolledError);

			polling = true;
		}

		private function handleCreatePolledResult(method:MediatorNodeCall, result:Object):void
		{
			logger.debug("handleCreatePolledResult");
			pollID = result as String;

			logger.debug("poll id: {0}", pollID);
			startPollTimer();
		}

		private function startPollTimer():void
		{
			pollAll();
			pollTimer = new Timer(5000); // every five seconds for now
			pollTimer.addEventListener(TimerEvent.TIMER, handlePollTimer);
			pollTimer.start();
		}

		private function pollAll():void
		{
			polling = true;

			var call:MediatorNodeCall = _node.execute("poll_all", [ pollID ]);
			call.addCallback(handlePollChangedResult, handlePollChangedError);
		}

		private function handleCreatePolledError(method:MediatorNodeCall, result:Object):void
		{
			logger.error("handleCreatePolledError: {0}", result);
			cleanupPolling();
		}

		private function cleanupPolling():void
		{
			polling = false;
			pollID = null;

			if (pollTimer != null)
			{
				pollTimer.stop();
				pollTimer.removeEventListener(TimerEvent.TIMER, handlePollTimer);
				pollTimer = null;
			}

		}

		private function pollChanged():void
		{
			polling = true;
			var call:MediatorNodeCall = _node.execute("poll_all", [ pollID ]);
			call.addCallback(handlePollChangedResult, handlePollChangedError);
		}

		private function handlePollChangedResult(method:MediatorNodeCall, result:Object):void
		{
			logger.debug("poll changed result: {0}", result);

			for (var key:String in result)
			{
				var item:Object = result[key];

				//entityPresence[key.substring(1)] = item.value;
				// Had been getting value but now get null?
				if (item == null)
				{
					logger.warn("Item returned as null for key: {0}", key);

					//entityPresence[key] = 0;

					continue;

				}
				entityPresence[key] = item.value;

			}

			updatePollChangedPresences();
			polling = false;
		}


		private function handlePollChangedError(method:MediatorNodeCall, error:Object):void
		{
			logger.error("Error on poll changed: {0}", error);

			cleanupPolling();
		}

		private function handlePollTimer(event:TimerEvent):void
		{
			logger.debug("poll timer");
			if (polling)
			{
				logger.debug("polling, so ignoring");
				return;
			}
			pollChanged();
		}
		public function getEntity(entityPath:String, add:Boolean=true):Entity
		{
			if (cachedNames[entityPath] != null)
			{
				return cachedNames[entityPath] as Entity;
			}

			return loadEntity(entityPath, add);
		}

		/**
		 * Loads a branch from the manager based on the elements of the path
		 * The return is an entity rooted at the root entity manager root
		 */
		public function getBranch(branch:String):Entity
		{
			// Trim the first "/", we don't need it
			if (branch.charAt(0) == "/")
			{
				 branch = branch.substring(1);
			}

			var segments:Array = branch.split("/");
			trace("segments: ");

			var subpath:String = "";
			var first:Entity = null;
			var lastNode:Entity = null;
			for each (var s:String in segments)
			{
				subpath += "/" + s;

				trace("\t" + subpath);

				var foundNode:Entity = null;

				if (cachedNames[subpath] != null)
				{
					trace("this is not nulL!");
					foundNode = cachedNames[subpath] as Entity;
				} else {
					foundNode = getEntity(subpath);

					if (lastNode != null)
					{
						// Here's the problem!
						//lastNode.children.addItem(foundNode);
						lastNode.addChild(foundNode);
					} else {
						addToEntities(foundNode);
					}
				}



				lastNode = foundNode;

				if (first == null)
				{
					first = lastNode;
				}

			}

			return first;

		}

		/*
		public function getRootEntities():ArrayCollection//path:String):ArrayCollection
		{
			// TODO Cache the collections
			var coll:ArrayCollection = new ArrayCollection();

			var call:MediatorNodeCall = _node.execute("get_entities_name", [ path ]);
			call.token = { 'root' : path, 'collection' : coll };

			call.addCallback(handleGetEntitiesResult, handleGetEntitiesError);

			return coll;
		}*/

		private function handleGetEntitiesResult(method:MediatorNodeCall, result:Object):void
		{
			var token:Object = method.token;

			var root:String = token['root'];
			var collection:ArrayCollection = token['collection'];

			//var newEntity:Entity = new Entity();

			// TODO Do not append children here, we should let the Node manager or service handle this for us
			//var node:MediatorNode = _node.getService().getNode(_node.path + "/" + name) as MediatorNode;

			//newEntity.initFromNode(node, name);

			for each (var name:String in result)
			{
				var fullPath:String = root + name;

				var newEntity:Entity = new Entity(this);

				// TODO Do not append children here, we should let the Node manager or service handle this for us
				var node:MediatorNode = _node.getService().getNode(_node.path + fullPath) as MediatorNode;

				newEntity.initFromNode(node, fullPath);
				collection.addItem(newEntity);

				cacheEntity(newEntity);
			}

		}

		private function handleGetEntitiesError(method:MediatorNodeCall, error:Object):void
		{
			var root:String = method.token.root;
			throw new Error("Unable to get entities at " + root);
		}

		public function get entities():ArrayCollection /* of IEntity */
		{
			if (!loaded)
			{
				logger.debug("entities were not loaded, loading");
				loadEntities();
			}

			return _entities;
		}

		private function updatePresences():void
		{
			for (var key:String in entityPresence)
			{
				var value:Object = entityPresence[key];
				var entity:Entity = cachedNames[key];

				if (entity != null)
				{
					// entity.status = value == 0 ? EntityStatus.OFF : EntityStatus.ON;
					// Handle the entityPresence dictionary (value = {'net':net,'framework':fw} )
					// as the value returns status objects on network and frame work status
					if(value['net'] == 0){
						entity.status = EntityStatus.NETWORK_OFF;
					} else if(value['framework'] == 0){
						entity.status = EntityStatus.FRAMEWORK_OFF;
					} else {
						entity.status = EntityStatus.ON;
					}
				}
			}
		}

		/**
		 * Used to update status of entity and all its parent after a poll change
		 *
		 * */
		private function updatePollChangedPresences():void
		{
			for (var entityKey:String in entityPresence)
			{
				var entityStatus:Object = entityPresence[entityKey];
				var entity:Entity = cachedNames[entityKey];

				if (entity != null)
				{
					if(entityStatus['net'] == 0){
						syncChildrenStatusWithPollChange(entity,-1);
						entity.status = EntityStatus.NETWORK_OFF;
						syncParentStatusWithPollChange(entity);

					} else if(entityStatus['framework'] == 0){
						syncChildrenStatusWithPollChange(entity,0);
						entity.status = EntityStatus.FRAMEWORK_OFF;
						syncParentStatusWithPollChange(entity);

					} else {
						syncChildrenStatusWithPollChange(entity,1);
						entity.status = EntityStatus.ON;
						syncParentStatusWithPollChange(entity);
					}

				}
			}
		}

		/**
		 * Sync All Parent Node Status recursively w.r.t the Poll Changed Node
		 **/
		private function syncParentStatusWithPollChange(node:Entity):void
		{
			var parentNode:Entity;
			if (node!= null)
            {
            	var nodePath:String = node.path;
            	var nodeStatus:int = node.status;
                var lastIndx:int = nodePath.lastIndexOf("/");
                if(lastIndx != -1 && lastIndx != 0)
				var path:String = node.path.substring(0,lastIndx);
				else
				path = null;
				if(path !=  null)
				{
				parentNode = getEntity(path);
				if(nodeStatus == EntityStatus.FRAMEWORK_OFF || nodeStatus == EntityStatus.NETWORK_OFF)
				parentNode.status = (parentNode.status != EntityStatus.LINK_OFF)?EntityStatus.LINK_OFF:parentNode.status;
				else
				parentNode.status = (parentNode.status != nodeStatus)?nodeStatus:parentNode.status;
				}
				else
				parentNode = null;
				syncParentStatusWithPollChange(parentNode);
            }

		}

		/**
		 * Sync All Children Node Status w.r.t the Poll Changed Node
		 **/
        private function syncChildrenStatusWithPollChange(pollChangedNode:Entity,newParentStatus:int):void
        {
        	var pollChngEntityPath:String = pollChangedNode.path;
        	var pollChngNodeLastSlashIndx:int = pollChngEntityPath.lastIndexOf("/");
        	var pollChngNodePathLen:int = pollChngEntityPath.length;
			var pollChngNodeLeaf:String = pollChngEntityPath.substring(pollChngNodeLastSlashIndx+1,pollChngNodePathLen);
        	for each (var entity:Entity in cachedCollection)
        	{
        		var isChildren:Boolean = false;
        		var childrenNodePath:String = null;
				if( entity.path != pollChangedNode.path)
				{
					var entityPath:String = entity.path;
					var segments:Array = entityPath.split("/");
						for each (var segment:String in segments)
						{
							if(segment == pollChngNodeLeaf)
							{
								isChildren = true;
								childrenNodePath = entityPath;
								break;
							}
						}
				}
				if(isChildren)
				{
				var childrenNode:Entity = getEntity(childrenNodePath)
				childrenNode.status = (childrenNode.status != newParentStatus)? newParentStatus:childrenNode.status;
				}
			}
        }

		/**
		 * Sync All Node Status with Parent Node Status while Loading Entity
		 **/
  		private function syncWithParentStatus(node:Entity):void
		{
			if (node!= null)
            {
            	var nodePath:String = node.path;
            	var nodeStatus:int = node.status;
                var lastIndx:int = nodePath.lastIndexOf("/");
                if((lastIndx != -1) && (lastIndx != 0))
				var path:String = node.path.substring(0,lastIndx);
				else
				path = null;
				if(path !=  null)
				{
				var parentNode:Entity = getEntity(path);
				node.status = (node.status != parentNode.status)?parentNode.status:nodeStatus;
				}
            }
  		}


		cisco_internal function loadEntities():void
		{
			logger.debug("loadEntites()");
			loaded = true;

//			var call:MediatorNodeCall = _node.execute("get_entity_names_for_ui", ["/"]);
			var call:MediatorNodeCall = _node.execute("get_entities_name", ["/"]);
			call.addCallback(handleChildrenNamesResult, handleChildreNamesError);
		}

		/**
		 * Result is an array of String with the names of the entities.
		 * Called from "loadEntites".
		 */
		private function handleChildrenNamesResult(method:MediatorNodeCall, result:Object):void
		{
			logger.debug("handleChildrenNamesResult({0}, {1})", method, result);

			parseChildrenNamesResult(result as Array);
		}

		private function handleChildreNamesError(method:MediatorNodeCall, error:Object):void
		{
			logger.error("handleChildrenNamesError({0}, {1})", method, error);

			throw new Error("Error getting children names: " + error);
		}
		
		private function addToEntities(entity:Entity):Boolean {
			if ( _entities != null && _entities.getItemIndex(entity) == -1) {
				_entities.addItem(entity);
				return true;
			}
			return false;
		}

		/**
		 * Loads the names of entities whose names have not been loaded yet.
		 *
		 * If any names are missing from the names array then those entities are
		 * removed.
		 */
		cisco_internal function parseChildrenNamesResult(names:Array /* of String */):void
		{
			logger.debug("parseChildrenNamesResult({0})", names);

			for each (var name:String in names)
			{
				if (cachedNames[name] != null)
				{
					continue;
				}

				logger.debug("New name detected for entity, creating new entity");
				var newEntity:Entity = loadEntity("/" + name);
				cacheEntity(newEntity);
				addToEntities(newEntity);
			}

			var missingNames:Array = []; // Keeps track of any names that are not in the array anymore
			for  (var cachedName:String in cachedNames)
			{
				var found:Boolean = false;
				for each (var name:String in names)
				{
					if (name == cachedName)
					{
						found = true;
						break;
					}
				}

				if (!found)
				{
					missingNames.push(name);
				}
			}

			logger.debug("Removing {0} entities", missingNames.length);

			for each (var name:String in missingNames)
			{
				removeEntity(name);
			}
		}

		/**
		 * Creates a new entity and caches it
		 */
		cisco_internal function loadEntity(name:String, add:Boolean=false):Entity
		{
			logger.debug("loadEntity({0})", name);

			// We find the last path that exists
			var segments:Array = name.split("/").splice(1); // We remove the first element because it's empty.
			var subpath:String = "";

			var lastEntity:Entity = null;
			for each (var segment:String in segments) {
				subpath += "/" + segment;

				var someEntity:Entity = cachedNames[subpath];

				if (someEntity == null) {
					// No entity found there, create a new one, add it to the children of the last entity
					var subNode:MediatorNode = _node.getService().getNode(_node.path + subpath) as MediatorNode;
					someEntity = new Entity(this);
					someEntity.initFromNode(subNode, subpath);
					cacheEntity(someEntity);

					if (lastEntity != null) {
						lastEntity.addChild(someEntity);//children.addItem(someEntity);
					}
				}

				lastEntity = someEntity;
			}

			updatePresences();
			syncWithParentStatus(lastEntity);
			
			return lastEntity;
		}

		public function cacheEntity(entity:Entity):void
		{
			logger.debug("caching entity: {0}", entity.path);

			if (cachedNames[entity.path] == null)
			{
				cachedNames[entity.path] = entity;
				cachedCollection.addItem(entity);
			}
		}

		cisco_internal function removeEntity(path:String):void
		{
			logger.debug("Removing entity '{0}'", path);
			delete cachedNames[path];

			for each (var entity:Entity in cachedCollection)
			{
				if (entity.path == path)
				{
					var idx:int = cachedCollection.getItemIndex(entity);
					cachedCollection.removeItemAt(idx);
					break;
				}
			}

			/*
			for each (var entity:Entity in _entities)
			{
				if (entity.path == path)
				{
					logger.debug("found and removing");
					entity.destroy();
					var idx:int = _entities.getItemIndex(entity);
					_entities.removeItemAt(idx);
					return;
				}
			}
			*/

			logger.debug("Unable to find entity '{0}'!", path);
		}
	}
}
