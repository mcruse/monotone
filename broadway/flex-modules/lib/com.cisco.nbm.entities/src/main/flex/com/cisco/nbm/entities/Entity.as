package com.cisco.nbm.entities
{
	import com.cisco.app.core.async.AsyncMethod;
	import com.cisco.cisco_internal;
	import com.cisco.nbm.xmlrpc.v2.MediatorNode;
	import com.cisco.nbm.xmlrpc.v2.MediatorNodeCall;
	
	import flash.events.EventDispatcher;
	import flash.events.TimerEvent;
	import flash.utils.Timer;
	
	import mx.collections.ArrayCollection;
	import mx.collections.Sort;
	import mx.collections.SortField;
	import mx.events.PropertyChangeEvent;
	import mx.logging.ILogger;
	import mx.logging.Log;
	import mx.utils.StringUtil;
	
	use namespace cisco_internal;
	
	[Event(name="entityPropertyChange", type="com.cisco.nbm.entities.EntityPropertyChangeEvent")]
	[Event(name="propertiesLoaded", type="com.cisco.nbm.entities.EntityEvent")]
	[Event(name="displayLoaded", type="com.cisco.nbm.entities.EntityEvent")]
	[Event(name="overrideComplete", type="com.cisco.nbm.entities.EntityPropertyOverrideEvent")]
	[Event(name="overrideError", type="com.cisco.nbm.entities.EntityPropertyOverrideEvent")]
	
	public class Entity extends EventDispatcher implements IEntity
	{
		private var _label:String;
		
		private var _properties:ArrayCollection /* of EntityPropertys */ = new ArrayCollection();
		
		cisco_internal var _node:MediatorNode;
		
		public var propertiesLoaded:Boolean = false;
		
		private static const logger:ILogger = Log.getLogger("cisco.nbm.entities.Entity");
		
		private var pollSID:String;
		
		private var pollCreateCalled:Boolean = false;
		
		private var pollTimer:Timer;
		
		private var polling:Boolean = false;
		
		private var initialPolled:Boolean = false;
		
		public static const POLL_DELAY:int = 5000;
		
		public var childrenLoaded:Boolean = false;
		
		private var _children:ArrayCollection = null;//new ArrayCollection();
		
		private var _display:String;
		
		private var _path:String;
		
		public var displayLoaded:Boolean = false;
		
		private var manager:EntityManager;		
		
	
		private var _status:int = EntityStatus.NONE_STATUS;
		
		/**
		 * This is the "entity" attribute of the "Entity" property
		 */
		private var _canonicalPath:String; 
		
		private var childrenCreated:Boolean = false;
		
		public function Entity(manager:EntityManager)
		{
			this.manager = manager;
		}
		
		public function get canonicalPath():String
		{
			return _canonicalPath;
		}

		public function get status():int
		{
			return _status;
		}
		[Bindable]
		public function set status(value:int):void
		{
			var oldValue:int = _status;
			
			_status = value;
			
			if (_status == EntityStatus.NETWORK_OFF)
			{
				
			}
			
			if (_status == EntityStatus.ON && (oldValue == EntityStatus.NETWORK_OFF || oldValue == EntityStatus.FRAMEWORK_OFF))
			{
				// Remove all the children and reload ...
				if (_children != null)
				{
					for each (var child:Entity in _children)
					{
						child.destroy();
					}
					_children.removeAll();
				}
				
				loadChildren();
			}
			
		}
		
		public function get display():String
		{
			return _display;
		}
		
		public function get path():String
		{
			return _path;
		}
		
		public function get children():ArrayCollection 
		{
			if (!childrenLoaded)
			{
				loadChildren();
			}
			
			return _children;
		}
		
		public function addChild(child:Entity):void
		{
			trace("add child at: " + this.label + " with child name " + child.label);
			//logger.debug("add child: " + childrenLoaded +", " + _children + ", " + child.label);
			if (_children == null)
			{
				createChildrenCollection();
				
				if (!childrenLoaded)
				{
					loadChildren();				
				}
				
			}
			
			// Find the child and do not add if already present
			for each (var exitingChild:Entity in _children)
			{
				if (exitingChild.path == this.path)
				{
					return
				}
			}
			
			_children.addItem(child);
		}
		
		public function loadChildren():void
		{
			childrenLoaded = true;
			
//			var call:MediatorNodeCall = _node.execute("get_entity_names_for_ui", []);
			var call:MediatorNodeCall = _node.execute("get_entities_name", []);
			call.addCallback(handleLoadChildrenResult, handleLoadChildrenFail);
		}
		
		private function handleLoadChildrenResult(method:MediatorNodeCall, result:Object):void
		{
			parseChildren(result as Array);
		}

		private function createChildrenCollection():void
		{	
			if (childrenCreated) {
				return;
			}
			
			childrenCreated = true;
			
			_children = new ArrayCollection();
			
			var sort:Sort = new Sort();
			sort.compareFunction = sortCompareFunction;
			sort.fields = [new SortField("label",true,false,true)];
			_children.sort = sort;
			_children.refresh();

		}
		
		private function parseChildren(result:Array):void
		{
			if (result.length == 0)
			{
				_children = null;
			}
			else
			{
				if (_children == null)
				{
					createChildrenCollection();
				}
				
				for each (var name:String in result)
				{
					// There's an inconsistency with the forward slashes attached to nodes
					// so we have to be sure not to append it if it's already included.
					
					// find out if it doesn't exist
					var proposedPath:String = path + "/" + name;
					var found:Boolean = false;
					
					for each (var child:Entity in _children)
					{
						if (proposedPath == child.path)
						{
							trace("***** SKIPPING : " + proposedPath + " from adding to " + child.path);
							found = true;
							break;
						}
					}
					
					if (found)
					{
						// Previously, returning would cause some children
						// not to be displayed.  However, now the selection gets lost
						// as new items are added.
						continue;
					}
			
					var entity:Entity = manager.getEntity(proposedPath, false);//new Entity(manager);
					
					// _node.getService().getNode(_node.path + "/" + nodeName) 
					//entity.initFromNode( _node.getService().getNode( _node.path + "/" + name) as MediatorNode, _path + "/" + name);
					// TODO Removed this add because it's added to the child by get entity....
					//_children.addItem(entity);
					
					//manager.cacheEntity(entity);
				}
			}
			
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "children", null, _children));
			dispatchEvent(new EntityEvent(EntityEvent.CHILDREN_LOADED));
		}
		
		private function handleLoadChildrenFail(method:MediatorNodeCall, error:Object):void
		{
			throw new Error("Unable to load entity '" + _node.name + "' children: " +  error); 
		}
		
		public function startPoll():void
		{
			logger.debug("startPoll");
			if (pollCreateCalled)
			{
				return;
			}
			
			pollCreateCalled = true;
			var call:MediatorNodeCall = _node.execute("create_polled", null);
			call.addCallback(handleCreatePolledResult, handleCreatePolledError);
		}
		
		private function handleCreatePolledResult(method:MediatorNodeCall, result:Object):void
		{
			pollSID = result as String;
			
			startPollTimer();
			internal_doPoll();
		}
		
		private function handleCreatePolledError(method:MediatorNodeCall, error:Object):void
		{
			throw new Error("Error creating polled: " + error);
		}
		
		private function startPollTimer():void
		{
			pollTimer = new Timer(POLL_DELAY);
			
			pollTimer.addEventListener(TimerEvent.TIMER, handlePollTimer);
			pollTimer.start();
		}
		
		public function stopPoll():void
		{
			if (pollCreateCalled && pollSID != null)
			{
				_node.execute("destroy", [ pollSID ]);
				
				stopPollTimer();
			}
			
			pollCreateCalled = false;
			pollSID = null;
		}
		
		private function stopPollTimer():void
		{
			pollTimer.stop();
			pollTimer.removeEventListener(TimerEvent.TIMER, handlePollTimer);
			pollTimer = null;
			initialPolled = false;
			polling = false;
		}
		
		private function handlePollTimer(event:TimerEvent):void
		{
			internal_doPoll();
		}
		
		private function internal_doPoll():void
		{
			if (polling)
			{
				return;
			}
			
			polling = true;
			
			if (!initialPolled)
			{
				initialPolled = true;
				var call:MediatorNodeCall = _node.execute("poll_changed", [ pollSID ]);
				call.addCallback(handlePollAllResult, handlePollAllError);
			}
			else
			{
				var call:MediatorNodeCall = _node.execute("poll_changed", [ pollSID ]);
				call.addCallback(handlePollChangedResult, handlePollChangedError);
			}
			
		}
		
		private function handlePollAllResult(method:MediatorNodeCall, result:Object):void
		{
			updateProperties(result);
			polling = false;
		}
		
		private function handlePollAllError(method:MediatorNodeCall, error:Object):void
		{
			stopPoll();
			throw new Error("Error while getting poll all: " + error);
		}
		
		private function handlePollChangedResult(method:MediatorNodeCall, result:Object):void
		{
			updateProperties(result);
			polling = false;
		}
		
		private function updateProperties(propertiesChanges:Object):void
		{
			for (var key:String in propertiesChanges)
			{
				// Currently the result is returned as a string of 
				// the format: "('type', 'name')"
				// so we need to parse it.
				// We should get a better result eventually,
				// possibly as an array of ResultItem 
				// with the type and name in the structure rather than as a key
				var formattedKey:String = StringUtil.trim( 
					StringUtil.trimArrayElements(key.substr(1, key.length-2), "," ));
				var tokens:Array = formattedKey.split( ",");
				
				var propertyType:String = (tokens[0] as String).substr(1, tokens[0].length-2); 
				var propertyName:String = (tokens[1] as String).substr(1, tokens[1].length-2);
				
				var change:Object = propertiesChanges[key];
				
				var property:EntityProperty = getPropertyByNameAndType(propertyName, propertyType);
				
				if (property == null)
				{
					continue;
				}
				
				if (change == null)
				{
					continue;
				}
				
				var value:Object = change['value'];
				
				property.value = value;
				
				var event:EntityPropertyChangeEvent = new EntityPropertyChangeEvent(this, property, value);
				dispatchEvent(event);
			}
		}
		
		public function getPropertyByName(name:String):EntityProperty
		{
			for each (var prop:EntityProperty in _properties)
			{
				if (prop.name == name)
				{
					return prop;
				}
			}
			
			return null;
		}
		
		public function getPropertyByNameAndType(name:String, type:String):EntityProperty
		{
			for each (var prop:EntityProperty in _properties)
			{
				if (prop.name == name && prop.type == type)
				{
					return prop;
				}
			}
			
			return null;
		}
		
		private function handlePollChangedError(method:MediatorNodeCall, error:Object):void
		{
			stopPoll();
			throw new Error("Error while getting poll changed: " + error);
		}
		
		public function get properties():ArrayCollection
		{
			return _properties;
		}
		
		cisco_internal function initFromNode(node:MediatorNode, name:String):void
		{
			_node = node;
			_path = name;
			label = _node.name;
			
			//loadProperties();
		}
		
		public function set label(value:String):void
		{
			if (_label != value)
			{
				var oldValue:String = _label;
				
				_label = value;
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "label", oldValue, _label));
			}
		}
		
		public function get label():String
		{
			return _label;
		}
		
		public static function sortCompareFunction(item1:Entity,item2:Entity,fields:Object=null):int {
			var label1:String = item1.label;
			var label2:String = item2.label;
			var anIndex:int = label1.toLowerCase().localeCompare(label2.toLowerCase());
			if ( anIndex < 0 ) {
				anIndex = -1;
			} else if ( anIndex > 0 ) {
				anIndex = 1;
			}
			/* if (sortField.descending)
           		anIndex *= -1; */
			return anIndex;
		}
		
		public function loadProperties(force:Boolean=false):void
		{
			if (propertiesLoaded && !force)
			{
				return;
			}
			
			var call:MediatorNodeCall = _node.execute("get_property_list", null);
			call.addCallback(handleGetPropertyListResult, handleGetPropertyListError);
		}		
		
		private function handleGetPropertyListResult(method:MediatorNodeCall, result:Object):void
		{
			logger.debug("handleGetPropertyListResult({0}, {1})", method, result);
			
			parsePropertyListResult(result as Array);
			
			//getWriteableList();
		}
		
		private function getWriteableList():void {
			logger.debug("getWriteableList");
			
			_node.execute("get_writeable_list", null)
				.addCallback(handleGetWriteableListResult, handleGetWriteableListError);
		}
		
		private function handleGetWriteableListResult(method:MediatorNodeCall, result:Object):void {
			logger.debug("Writeable List Retrieved: {0}", result);
			
			for (var i:int = 0; i < (result as Array).length; i++) {
				
				var tuple:Array = result[i] as Array;
				logger.debug("Checking tuple: " + tuple[0] + "=" + tuple[1]);
				for each (var p:EntityProperty in properties) {
					if (p.type == tuple[0] && p.name == tuple[1]) {
						p.canWrite = true;
					}
				}
			}
			
		}
		
		private function handleGetWriteableListError(method:MediatorNodeCall, error:Object):void {
			logger.debug("Error retrieving list: {0}", error);
		}
		
		private function handleGetPropertyListError(method:MediatorNodeCall, error:Object):void
		{
			logger.error("handleGetPropertyListError({0}, {1})", method, error);
			throw new Error("error getting property list for entity " + _label + ": " + error);
		}
		
		private function parsePropertyListResult(list:Array):void
		{	
			// TODO This is a temporary patch for list being returned as 
			// a python source string.
			/*
			for each (var source:String in list)
			{
				var decoder:JSONDecoder = new JSONDecoder(source);
				var parsed:Object = decoder.getValue();
				
				var property:EntityProperty = new EntityProperty();
				property.fromObject(parsed);
				
				_properties.addItem(property);
			}
			*/
			
			
			
			for each (var item:Object in list)
			{
				var property:EntityProperty = new EntityProperty();
				property.fromObject(item);
				_properties.addItem(property);
			
				// NOTE This is a bit of ahack
				if (item['name'] == "Entity")
				{
					_canonicalPath = item['entity'];
					_display = item['url'];
					status = item['value'];
				}
				
			}
			
			
			propertiesLoaded = true;
			dispatchEvent(new EntityEvent(EntityEvent.PROPERTIES_LOADED));
			//dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "properties", null, _properties));
			//loadDisplay();
		}
		
		public function loadDisplay():void
		{
			var call:MediatorNodeCall = _node.execute("get_display", null);
			call.addCallback(handleLoadDisplayResult, handleLoadDisplayError);
		}
		
		private function handleLoadDisplayError(method:MediatorNodeCall, error:Object):void
		{
			throw new Error("Unable to load display for entity '" + label + "': " + error);
		}
		
		private function handleLoadDisplayResult(method:MediatorNodeCall, result:Object):void
		{
			_display = result as String;
			//propertiesLoaded = true;
			displayLoaded = true;
			dispatchEvent(new EntityEvent(EntityEvent.DISPLAY_LOADED));
		}
		
		cisco_internal function destroy():void
		{
			logger.debug("Destroy entity {0}", _label);
			
			for each (var property:EntityProperty in _properties)
			{
				//delete _properties[propertyName]
				//property.destroy();
			}
			
			if (_children != null)
			{
				for each (var child:Entity in _children)
				{
					child.destroy();
				}
			}
			
			if (manager != null)
			{
				manager.removeEntity(path);
			}
			
			_properties.removeAll();
			
			_node.destroy();
			_node = null;
		}
		
		override public function toString():String
		{
			trace("To string getting called");
			return "Entity(label="+_label+", " + _properties + ")";
		}
		
		public function getPropertyOverride(property:EntityProperty):AsyncMethod
		{
			var call:MediatorNodeCall = _node.execute("get_override", 
				[  property.type, property.name ]);
			call.token = property;
			call.addCallback(handleGetOverrideResult, handleGetOverrideError);
			
			return call; 
		}
		
		public function setPropertyOverride(property:EntityProperty, overrides:Object):AsyncMethod
		{
			if (!property.canWrite) {
				logger.warn("Tried to write to a property that cannot be overwriten by current user");
				return null;
			}
			
			var call:MediatorNodeCall = _node.execute("override_property",
				[ property.type, property.name, overrides ]);
			call.token = { 'property' : property,
				'overrides' :  overrides };
			call.addCallback(handleSetOverrideResult, handleSetOverrideError);
			return call;
		}
		
		private function handleSetOverrideResult(method:MediatorNodeCall, result:Object):void
		{
			var token:Object = method.token;
			var property:EntityProperty = token.property;
			var overrides:Array = [];//token.overrides;
			// TODO Fix this
			// convert the overrides from an array
			for (var i:int = 0; i < 16; i++)
			{
				overrides.push( token.overrides[i+1] );
			}
			
			property.setOverrides(overrides);
			
			var entityPropertyOverrideEvent:EntityPropertyOverrideEvent =
				new EntityPropertyOverrideEvent(EntityPropertyOverrideEvent.ON_COMPLETE);
			entityPropertyOverrideEvent.entity = this;
			dispatchEvent(entityPropertyOverrideEvent);
		}
		
		private function handleSetOverrideError(method:MediatorNodeCall, error:Object):void
		{
			var entityPropertyOverrideEvent:EntityPropertyOverrideEvent =
				new EntityPropertyOverrideEvent(EntityPropertyOverrideEvent.ON_ERROR);
			entityPropertyOverrideEvent.entity = this;
			entityPropertyOverrideEvent.error = error.toString();
			dispatchEvent(entityPropertyOverrideEvent);
			
			throw new Error("Unable to set override: " + error);
		}
		
		private function handleGetOverrideResult(method:MediatorNodeCall, result:Object):void
		{
			var property:EntityProperty = method.token as EntityProperty;
			
			property.setOverrides(result);
		}
		
		private function handleGetOverrideError(method:MediatorNodeCall, error:Object):void
		{
			logger.error("Unable to get property override for {0}: {1}", method.token, error);
		}
		
	}
}