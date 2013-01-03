package com.cisco.nbm.scheduler
{
	import com.cisco.app.core.async.AsyncMethod;
	import com.cisco.cisco_internal;
	import com.cisco.nbm.scheduler.events.ScheduleEvent;
	import com.cisco.nbm.xmlrpc.v2.MediatorNode;
	import com.cisco.nbm.xmlrpc.v2.MediatorNodeCall;
	
	import flash.events.EventDispatcher;
	
	import mx.collections.ArrayCollection;
	import mx.collections.Sort;
	import mx.collections.SortField;
	import mx.events.PropertyChangeEvent;
	import mx.logging.ILogger;
	import mx.logging.Log;


	[Event(name="metaDataUpdated", type="com.cisco.nbm.scheduler.events.ScheduleEvent")]
	[Event(name="dailyEntryUpdated", type="com.cisco.nbm.scheduler.events.ScheduleEvent")]
	[Event(name="propertyUpdated", type="com.cisco.nbm.scheduler.events.ScheduleEvent")]
	[Event(name="summaryComplete", type="com.cisco.nbm.scheduler.events.ScheduleEvent")]
	/**	
	 * Represents a schedule on the mediator.
	 * 
	 * When an object of this class is created it is set in an uninitialized state.
	 * 
	 * Initialization requires several asynchronous requests and these are outlined below.
	 * Each call is to the node specified during initFromNode.  After each call is
	 * complete it invokes the call beneath it.  The final call dispatches 
	 * SUMMARY_COMPLETE and COMPLETE.
	 * 
	 * <b>get_summary()<b/>
	 * <p>Returns Entries (the times and values set) and Exceptions.</p>
	 * 
	 * <b>get_event_meta()</b>
	 * <p>Gets the event-related metadata values.  These are the values  
	 * that get sent to devices when an event is executed.  These are
	 * also the values that you can edit in the Options tab of the schedule editor.
	 * 
	 * For example:  
	 * 
	 * 	color, name, value
	 * 
	 * If the schedule has no event_meta values then two default values are created:
	 * 
	 * OFF and ON with the following values:
	 * 
	 * { color: XXX, name : "Off", value : 0 }
	 * { color: YYY, name : "On" , value : 1 }
	 * 
	 * </p>
	 * 
	 * <b>get_properties</b>
	 * <p>Properties are the things that the schedule drives.  The values
	 * returned by this call are the property paths themselves and the
	 * value mapping between property values and event meta.
	 * </p>
	 * <p>For example:
	 * 		"property":"/path/to/entity/prop",
     *      "type":"property_type",
	 * 		"valuemap":{"eventname":"eventvalue"}}]</p>
	 * 
	 * <p>This is the step where the valuemapping between properties
	 * and events needs to happen because otherwise we get problems
	 * where the user modifies the eventmeta and the valuemaps get
	 * incorrectly updated.
	 * </p>
	 * 
	 * <b>get_meta()</b>
	 * <p>Gets override and immutable status.
	 * This is the final step and after this it dispatches the "complete" events.
	 * </p>
	 * 
	 */
	public class HierarchicalSchedule extends EventDispatcher
	{
		use namespace cisco_internal; 
		
		public static const DEFAULT_OFF_META_NAME:String = "Off";
		public static const DEFAULT_OFF_META_VALUE:String = "0";
		public static const DEFAULT_OFF_META_COLOR:int = 0x00FF00;
		
		public static const DEFAULT_ON_META_NAME:String = "On";
		public static const DEFAULT_ON_META_VALUE:String = "1";
		public static const DEFAULT_ON_META_COLOR:int = 0xFF0000;
		
		private var _dailyEntries:ArrayCollection = new ArrayCollection();
		
		
		public var _node:MediatorNode;
		
		[Bindable]
		public var name:String;
		
		[Bindable]
		public var _children:ArrayCollection = new ArrayCollection();
		
		[Bindable]
		public var parent:HierarchicalSchedule;
		
		[Bindable]
		public var metaData:ArrayCollection /* of EventMetaData */ = new ArrayCollection();
		//public var metaData:EventMetaData = new EventMetaData();
		
		private var _exceptions:ArrayCollection = new ArrayCollection();
		
		private var _overrideStatus:Boolean = false;
		
		private static var logger:ILogger = Log.getLogger("cisco.nbm.scheduler.HierarchicalSchedule");
		
		public static const MONDAY:String = "monday";
		public static const TUESDAY:String = "tuesday";
		public static const WEDNESDAY:String = "wednesday";
		public static const THURSDAY:String = "thursday";
		public static const FRIDAY:String = "friday";
		public static const SATURDAY:String = "saturday";
		public static const SUNDAY:String = "sunday";
		
		public static const DAY_INDEXES:Array = [ SUNDAY, MONDAY, TUESDAY,
			WEDNESDAY, THURSDAY, FRIDAY, SATURDAY ];

		
		cisco_internal var _loadedChildren:Boolean = false;
		
		public var initialized:Boolean = false;
		
		private var initializedCalled:Boolean = false;
		
		public var properties:ArrayCollection = new ArrayCollection();
		
		private var propertiesLoaded:Boolean;
		
		private var metaLoaded:Boolean;
		
		public var blockCalls:Boolean = false;
		
		[Bindable]
		public var online:Boolean = true;
		
		
		public var _readOnly:Boolean = true;
		
		cisco_internal var _isRemote:Boolean = false;
		
		cisco_internal var _isRemoteRoot:Boolean = false;
		
		/**
		 * This flag indicates that the schedule needs updating for any reason 
		 * such as, for example, the parent having its override changed
		 * and thus the children needing updates.  It's usually used by the
		 * navigator so that it can fetch new data for the children of parents
		 * who've had the override set or released.
		 */
		[Bindable]
		public var needUpdating:Boolean = false;
		
		public function HierarchicalSchedule()
		{
			super();
			
			for (var i:int = 0; i < DAY_INDEXES.length; i++)
			{
				_dailyEntries.addItem(new ArrayCollection());
			}
		}
		
		public function get isRemote():Boolean {
			return _isRemote;
		}
		
		public function get isRemoteRoot():Boolean {
			return _isRemoteRoot;
		}
		
		/**
		 * Must update all daily entries when the event meta is updated.
		 * 
		 * This is brittle and will instead require that the schedule meta
		 * be loaded before the schedule can be edited.
		 */
		public function updateMetaEntry(metaEntry:EventMetaData, 
			newName:String, newColor:int, newValue:String):void
		{
			var oldValue:Object = metaEntry.value;
			if (metaEntry != null)
			{
				metaEntry.name = newName;
				metaEntry.color = newColor;
				metaEntry.value = newValue;
			}
			
			for each (var dayName:String in DAY_INDEXES)
			{
				var coll:ArrayCollection = getEntriesForDay(dayName);
				
				for each (var dailyEntry:DailyEntry in coll)
				{
					if (dailyEntry.eventMeta == metaEntry)
					{
						dailyEntry.updateFromMeta();
					}
				}
			} 
			
			// Change exceptions
			for each (var exceptionEntry:ScheduleExceptionEntry in _exceptions)
			{
				for each (var exceptionDailyEntry:DailyEntry in exceptionEntry.timeValueEntries)
				{
					if (exceptionDailyEntry.eventMeta == metaEntry)
					{
						exceptionDailyEntry.updateFromMeta();
					}
				}
			}
			
			// Change proeprties 
			// TODO Properties must be loaded otherwise their value map
			// will not be updated properly.
			if (!propertiesLoaded)
			{
				throw new Error("Properties were not loaded.  Must load before " + 
						"updating event meta");
			}
			/*
			for each (var prop:ScheduleProperty in properties)
			{
				for (var vmEntryKey:Object in prop.valuemap)
				{
					if ((""+vmEntryKey) == (""+oldValue))
					{
						// delete old entry, set new entry
						// TODO This is brittle, again
						var val:Object = prop.valuemap[vmEntryKey];
						delete prop.valuemap[vmEntryKey];
						prop.valuemap[metaEntry.value] = val;
						
					}
					
				}
			}
			*/
			// NOTE: If the metadata event is dispatched then the metadata editor loses focus
			// 		If it is not dispatched, then the daily schedule editors don't update their colors 
			var event:ScheduleEvent = new ScheduleEvent(ScheduleEvent.METADATA_UPDATED);
			event.item = metaEntry;
			dispatchEvent(event);
		}
		
		/**
		 * Update an existing daily entry.
		 * 
		 * Do not update the daily entry itself directly becaues
		 * we want the schedule to dispatch an update event when
		 * an update occurs
		 */
		public function updateDailyEntry(entry:DailyEntry, 
			newTime:int, newDay:String):void
		{
				
		}
		
		public function getEntityRoot():MediatorNodeCall
		{
			var call:MediatorNodeCall = _node.execute("get_entity_root", []);
			
			return call;
		}
		
		public function deleteEventMetaEntry(entry:EventMetaData):void
		{
			var idx:int = metaData.getItemIndex(entry);
			
			if (idx == -1)
			{
				return;
			}
			
			// Find all daily entries with event meta name and delete it
			for each (var dayName:String in DAY_INDEXES)//(var coll:ArrayCollection in _dailyEntries)
			{
				var deleteEntries:Array = [];
				var coll:ArrayCollection = getEntriesForDay(dayName);
				
				for each (var dailyEntry:DailyEntry in coll)
				{
					if (dailyEntry.value == entry.value)
					{
						deleteEntries.push(dailyEntry);	
					}
				}
				
				for each (dailyEntry in deleteEntries)
				{
					this.removeDailyEntry(dayName, dailyEntry);
				}
			}
			
			metaData.removeItemAt(idx);
			var event:ScheduleEvent = new ScheduleEvent(ScheduleEvent.METADATA_UPDATED);
			event.item = entry;
			dispatchEvent(event);
		}
		
		public function markChildrenNeedUpdating(value:Boolean):void
		{
			for each (var child:HierarchicalSchedule in _children)
			{
				child.needUpdating = value;
				child.markChildrenNeedUpdating(value);
			}
			 
		}
		
		public function initialize(force:Boolean=false):void
		{
			if (force)
			{
				initialized = false;
			}
			
			if (initialized)
			{
				return;
			}
			
			if (initializedCalled && !force)
			{
				return;
			}
			
			if (blockCalls)
			{
				return;
			}
			
			initializedCalled = true;
			fetchData();
			//getEventMeta();			
		}

		[Bindable]
		public function get overrideStatus():Boolean
		{
			return _overrideStatus;
		}
		
		public function set overrideStatus(value:Boolean):void
		{
			_overrideStatus = value;
		}
		
		[Bindable]
		public function get readOnly():Boolean
		{
			return _readOnly;
		}
		
		public function set readOnly(value:Boolean ):void
		{
			throw new Error("This is a read only property");
		}
		
		public function removeDailyEntry(dayName:String, entry:DailyEntry):void
		{
			var entries:ArrayCollection = getEntriesForDay(dayName);
			var idx:int = entries.getItemIndex(entry);
			
			if (idx != -1)
			{
				entries.removeItemAt(idx);
				var event:ScheduleEvent = new ScheduleEvent(ScheduleEvent.DAILENTRY_UPDATED);
				event.item = entry;
				dispatchEvent(event);
			}
		}
		
		public function getEventMeta():void
		{
			if (!metaLoaded && !blockCalls)
			{
				var call:MediatorNodeCall =_node.execute("get_event_meta", null);
				call.addCallback(handleGetEventMetaResult, handleGetEventMetaError);
			} else {
				getProperties();
			}
		}
		
		public function updateEventMeta():MediatorNodeCall
		{
			var event_meta_object:Object = {};
			
			// catch the possibility of the event meta being empty here
			if (metaData.length == 0)
			{
				createDefaultEventMeta();
			}
			
			var i:int = 0;
			for each (var eventMetaEntry:EventMetaData in metaData)
			{
				var entry:Object =  
					{ 'name' : eventMetaEntry.name, 'color' : eventMetaEntry.color };
					
				if (i == 0)
				{
					entry['default'] = 1;
				}
				
					
				event_meta_object[eventMetaEntry.value] = entry;
				
				i++
			}
			
			var call:MediatorNodeCall = _node.execute("set_event_meta", 
				[event_meta_object]);
			call.addCallback(handleUpdateEventMetaResult, handleUpdateEventMetaError);
			
			return call;
		}
		
		public function moveMetaData(sourceIndex:int, destIndex:int):void
		{
			var item:Object = metaData.removeItemAt(sourceIndex);
			metaData.addItemAt(item, destIndex);
			
			var event:ScheduleEvent = new ScheduleEvent(ScheduleEvent.METADATA_UPDATED);
			event.item = item;
			dispatchEvent(event);
		}
		
		private function handleUpdateEventMetaResult(method:AsyncMethod, result:Object):void
		{
			logger.debug("metaUpdated");
		}
		
		private function handleUpdateEventMetaError(method:MediatorNodeCall, error:Object):void
		{
			processException("Unable to update event meta: " + error, method, error);
		}
		
		private function handleGetEventMetaError(method:MediatorNodeCall, error:Object):void
		{
			processException("Unable to get event meta: " + error, method, error);
		}
		
		
		/**
		 * Return count entries associated with event meta data
		 */
		public function getCountEntriesForEventMeta(meta:EventMetaData):int
		{
			var count:int = 0;
			
			for each (var coll:ArrayCollection in _dailyEntries)
			{
				for each (var entry:DailyEntry in coll)
				{
					if (entry.eventMeta == meta)
					{
						count++;
					}
				}
			}
			
			return count;
		}
		
		private function handleGetEventMetaResult(method:AsyncMethod, result:Object):void
		{
			logger.debug("handleGetEventMetaResult({0})", result);

			metaData.removeAll();

			// We keep track of the number of parsed entry.  If the number
			// of parsed entries is 0 then we need to create a set of default
			// event meta data entries.
			var parsedCount:int = 0;
			
			if (result != null)
			{
				for (var valueKey:String in result) 
				{
					// Check for invalid meta name and skip ...
					if (!result[valueKey].hasOwnProperty("name"))
					{
						logger.warn("Event meta for schedule: " + this.name + " is invalid");
						continue;
					}
					
					var newMeta:EventMetaData = new EventMetaData();
					newMeta.value = valueKey;
					
					
					newMeta.name = result[valueKey]['name'];
					newMeta.color = new Number(result[valueKey]['color']);
					
					if (result[valueKey]['default'] == "1")
					{
						metaData.addItemAt(newMeta, 0);
					}
					else
					{
						metaData.addItem(newMeta);
					}
					
					parsedCount++;
				}
			}


			// No entries? Create default.			
			if (parsedCount == 0)
			{
				createDefaultEventMeta();
			}
			
			metaLoaded = true;
			
			updateDailyEntries();
			updateExceptions();
			
			getProperties();
		}
		
		private function createDefaultEventMeta():void
		{
			logger.debug("Creating default event meta");
			
			var offMeta:EventMetaData = new EventMetaData();
			offMeta.color = DEFAULT_OFF_META_COLOR;
			offMeta.name = DEFAULT_OFF_META_NAME;
			offMeta.value = DEFAULT_OFF_META_VALUE;
			
			var onMeta:EventMetaData = new EventMetaData();
			onMeta.color = DEFAULT_ON_META_COLOR;
			onMeta.name = DEFAULT_ON_META_NAME;
			onMeta.value = DEFAULT_ON_META_VALUE;
			
			metaData.addItem(offMeta);
			metaData.addItem(onMeta);
		}
		
		private function updateExceptions():void
		{
			for each (var exceptionEntry:ScheduleExceptionEntry in _exceptions)
			{
				for each (var dailyEntry:DailyEntry in exceptionEntry.timeValueEntries)
				{
					// trying to find event meta for daily entry, if not found, send warning
					var found:Boolean = false;
					
					for each (var metaEntry:EventMetaData in metaData)
					{
						if (metaEntry.value == dailyEntry.value)
						{
							found = true;
							dailyEntry.eventMeta = metaEntry;
							//dailyEntry.updateFromMeta();
							break;
						}
					}
					
					if (!found)
					{
						logger.warn("**** UNABLE TO FIND EVENT WITH VALUE {0} FOR EXCEPTION {1} AND DAILY ENTRY: {2}",
							dailyEntry.value, exceptionEntry.name, dailyEntry.name);
							 
					}
				}
			}
		}
		
		/**
		 * Match the event name to the daily entry
		 */
		private function updateDailyEntries():void
		{
			for each (var metaEntry:EventMetaData in metaData)
			{
				for each (var dayName:String in DAY_INDEXES)
				{
					var coll:ArrayCollection = getEntriesForDay(dayName);
					
					for each (var entry:DailyEntry in coll)
					{
						if (metaEntry.value == entry.value)
						{
							entry.eventMeta = metaEntry;
						//	entry.updateFromMeta();
						} 
					}
				}
			}
		}
		
		public function replaceProperties(newProperties:Array):Boolean
		{
			var propertiesUpdated:Boolean = false;
			
			var removeProps:Array = [];
			// remove any properties that do not match
			for each (var existingProp:ScheduleProperty in properties)
			{
				var found:Boolean = false;
				
				for each (var newProp:ScheduleProperty in properties)
				{
					if (existingProp.isEqual(newProp))
					{
						found = true;
						break;
					}
				}
				
				if (!found)
				{
					removeProps.push(existingProp);
				}
			}
			
			
			if (removeProps.length > 0)
			{
				logger.debug("Will remove: " + removeProps.length + " properties");
				propertiesUpdated = true;
				
				for each (var prop:ScheduleProperty in removeProps)
				{
					var idx:int = properties.getItemIndex(prop);
					properties.removeItemAt(idx);
				}
			}
			
			// Now we add just the props that are not already existing
			for each (var newProp:ScheduleProperty in newProperties)
			{
				var found:Boolean = false;
				for each (var existingProp:ScheduleProperty in properties)
				{
					if (existingProp.isEqual(newProp))
					{
						found = true;
						break;
					}
				}
				
				if (!found)
				{
					properties.addItem(newProp);
					propertiesUpdated = true;
				}
			}
			
			if (propertiesUpdated)
			{
				var event:PropertyChangeEvent = 
				PropertyChangeEvent.createUpdateEvent(this, "properties",
				null, properties);
				dispatchEvent(event);
				
				var scheduleEvent:ScheduleEvent = new ScheduleEvent(ScheduleEvent.PROPERTY_UPDATED);
				
				dispatchEvent(scheduleEvent);
				
				return true;
			}
			
			return false;
		}
		
		public function updatePropertyValueMap(property:ScheduleProperty, newValueMap:Object):Boolean
		{
			var updated:Boolean = false;
			
			// New map returns UUID => New Value
			for (var uuid:String in newValueMap) {
				var newValue:String = newValueMap[uuid];
				var existingValue:String = property.valuemap[uuid];
				
				if (existingValue != newValue) {
					updated = true;
					property.valuemap[uuid] = newValue;
				}
			} 
			
			return updated;
		}
		
		private function getMeta():void
		{
			var call:MediatorNodeCall = _node.execute("get_meta", null);
			call.addCallback(handleGetMetaResult, handleGetMetaError);			
		}
		
		private function handleGetMetaResult(method:AsyncMethod, result:Object):void
		{
			logger.debug("handleGetMetaResult({0})", result);
			
			var oldValue:Boolean = _overrideStatus;
			
			_overrideStatus = new Boolean(result['override']);
			
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this,
				"overrideStatus", oldValue, _overrideStatus));
			
			oldValue = _readOnly;
			
			_readOnly = new Boolean(result['immutable']);
			
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this,
				"readOnly", oldValue, _readOnly));
			
			// TODO Dispatch complete for different process
			initialized = true;
			setOnline(true);
			dispatchEvent(new ScheduleEvent(ScheduleEvent.SUMMARY_COMPLETE));
			dispatchEvent(new Event(Event.COMPLETE));
		}
		
		private function setOnline(value:Boolean):void
		{
			if (value == online)
			{
				return;
			}
			
			var oldValue:Boolean = online;
			logger.debug("setting schedule: " + name + " to online: " + value);
			online = value;
			
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this,
				"online", oldValue, online));
		}
		
		// TODO For now we add this
		public function updateOverrideStatus():void
		{
			var call:MediatorNodeCall = _node.execute("set_override", [ _overrideStatus ]);
			call.addCallback(handleSetOverrideStatusResult, handleSetOverrideStatusError);
		}
		
		private function handleSetOverrideStatusResult(method:AsyncMethod, result:Object):void
		{
			logger.debug("handleSetOverrideStatusResult({0})", result);
			
			// mark children as needing update
			markChildrenNeedUpdating(true);
			/*
			for each (var child:HierarchicalSchedule in _children)
			{
				child.needUpdating = true;
			}
			*/
			
			initializedCalled = false;
			
			//updateFromNode();
			//fetchData();
			initialize(true);
			
		}
		
		public function update():void
		{
			trace("::::::update!");
			//getChildren();
			initialize(true);
			needUpdating = false;
			//updateFromNode();
		}

		private function handleSetOverrideStatusError(method:MediatorNodeCall, result:Object):void
		{
			processException("Unable to set override status: " + result, method, result);
			//throw new Error("Unable to set override status: " + result);
		}
		
		private function handleGetMetaError(method:MediatorNodeCall, error:Object):void
		{
			processException("Unable to get meta information: " + error, method, error);
		}
		
		/**
		 * Loads one schedule 
		 */
		public function internalLoadChildSchedule(name:String):void
		{
			// check if child schedule already exists
			for each (var schedule:HierarchicalSchedule in _children)
			{
				if (schedule.name == name)
				{
					return;
					break;
				}
			}
			
			var schedule:HierarchicalSchedule = new HierarchicalSchedule();
			schedule.initFromNode(this, _node.getService().getNode(_node.path + "/" + name) as MediatorNode);
			
			_children.addItem(schedule);
		}
		
		public function forceGetChildren():void
		{
			if (!online)
			{
				logger.warn("Schedule is offline");
				return;
			}
			_loadedChildren = false;
			_children.removeAll();
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "children", null, _children));
			
			
			getChildren();
		}
		
		[Bindable]
		public function get children():ArrayCollection 
		{
			if (!_loadedChildren)
			{
				// NOTE Taking off to test query
			//	getChildren();
			}
			
			return _children;
		}
		
		public function set children(value:ArrayCollection):void
		{
			throw new Error("children is read-only");
		}
		
		public function initFromNode(parent:HierarchicalSchedule, node:MediatorNode):void
		{
			this.parent = parent;
			
			_node = node;
			
			if (parent != null)
			{
				if (parent.isRemote) {
					this._isRemote = parent._isRemote;
				}
				parent._node.internalAddChild(_node);
			}
			
			updateFromNode();
			
			//getProperties();
			//getChildren();
		}
		
		private function getProperties():void
		{
			if (blockCalls)
			{
				return;
			}
			var call:MediatorNodeCall = _node.execute("get_properties", null);
			call.addCallback(handleGetPropertiesResult, handleGetPropertiesError);
		}
		
		private function handleGetPropertiesResult(method:AsyncMethod, result:Object):void
		{
			logger.debug("handleGetPropertiesResult({0})", result);
			
			for each (var prop:Object in result)
			{
				logger.debug("\tproperty: '{0}'", prop);
				var property:ScheduleProperty = new ScheduleProperty();
				property.fromDictionary(prop);
				resolveEventMetaMappings(property);
				
				properties.addItem(property);
			}
			
			propertiesLoaded = true;
			//getEventMeta();
			//getOverrideStatus();
			getMeta();
		}
		
		private function resolveEventMetaMappings(property:ScheduleProperty):void {
			logger.debug("attempting to resolve value maps for: " + property.rawValueMap);
			
			for (var key:String in property.rawValueMap) {
				var value:Object = property.rawValueMap[key];
				for each (var eventMeta:EventMetaData in metaData) {
					if (key == eventMeta.value) {
						property.valuemap[eventMeta.uuid] = value;
						break;
					}
				}
			} 
			
			logger.debug("resolved values to: " + property.valuemap);
		}
		
		private function handleGetPropertiesError(method:MediatorNodeCall, error:Object):void
		{
			if (blockCalls)
			{
				return;
			}
			
			processException("Unable to get properties: " + error, method, error);
			//throw new Error("unable to get properties:" + error);
		}
		
		public function updateProperties():MediatorNodeCall
		{
			var propertyArray:Array = [];
			var eventName:String = "";
			
			for each (var property:ScheduleProperty in properties)
			{
				var dict:Object = property.toDictionary(metaData);
				
				//dict['valuemap'] = { /*'eventname' : eventName */};
				
				propertyArray.push(dict);
			}
			
			var call:MediatorNodeCall = _node.execute("set_properties", [ propertyArray ]);
			call.addCallback(handleUpdatePropertiesResult, handleUpdatePropertiesError);
			
			return call;
		}
		
		private function handleUpdatePropertiesResult(method:AsyncMethod, result:Object):void
		{
			logger.debug("update properties");
		}
		
		private function handleUpdatePropertiesError(method:MediatorNodeCall, error:Object):void
		{
			processException("Unable to set properties: " + error, method, error);
			//throw new Error("unable to set properties:" + error);
		}
		
		public function toSummary():Array
		{
			var summary:Array = [];
			
			var weeklySchedule:Array = [ ];
			var weeklyEntries:Array = [];
			for each (var name:String in DAY_INDEXES)
			{
				var weekEntry:Array = [ name ];
				
				var entryCollection:ArrayCollection = getEntriesForDay(name);
				
				for each (var entry:DailyEntry in entryCollection)
				{
					weekEntry.push( [ entry.name, entry.toMPXString(), entry.value ] );
				} 
				
				weeklyEntries.push(weekEntry);
				weeklySchedule.push(name);
				
			}
			
			var exceptionArray:Array = [ "exceptions" ];
			for each (var exception:ScheduleExceptionEntry in _exceptions)
			{
				var exceptionTVEntries:Array /* of Object */ = exception.entriesToSummaryArray();
				
				var exceptionWeeklyEntry:Array = [ exception.name ];
				
				for each (var exceptionEntry:Object in exceptionTVEntries)
				{
					//weeklyEntries.push( [ exception.name, exceptionEntry ] );
					exceptionWeeklyEntry.push( exceptionEntry );
				}
				
				weeklyEntries.push(exceptionWeeklyEntry);
				
				exceptionArray.push( exception.toMPXSummaryEntry() );
			}
			
			exceptionArray.push("weekly_schedule");
			
			summary.push(weeklyEntries);
			summary.push([["weekly_schedule", weeklySchedule]]);
			
			/*var exception_entry:Array = ["exceptions"];
			if (exceptionArray.length > 0)
			{
				exception_entry.push(exceptionArray);
			}*/
			
			//if (exceptionArray.length > 2)
			{
				summary.push([exceptionArray]);
			}
			
			//exception_entry.push("weekly_schedule");
			//summary.push([exception_entry]);
			//summary.push(["exceptions", exceptionArray]);
			summary.push("exceptions");
			// put the weekly_schedule entry
			
			
			return summary;
		}
		
		private function fetchData():void
		{
			// TODO Temporary fix for properties not getting loaded.
			//initializedCalled = true;
			getSummary();
		}
		
		private function getSummary():void
		{
			if (blockCalls)
			{
				return;
			}
			
			var call:MediatorNodeCall = _node.execute("get_summary", null);
			call.addCallback(handleGetSummary, handleGetSummaryError);
		}
		
		private function updateFromNode():void
		{
			name = _node.name;

			if (parent != null && parent.isRemote) {
				_isRemote = parent._isRemote; 
			}
			
			_isRemoteRoot = extractScheduleServerName(name) != null;
			
			if (_isRemoteRoot) {
				_isRemote = _isRemoteRoot;
			}
			
			// parse name to see if it's a remote root
			
			//_node.addEventListener(PropertyChangeEvent.PROPERTY_CHANGE, handleNodePropertyChange);
			
			//fetchData();
		}
		
		private function extractScheduleServerName(name:String):String
		{
			var startIdx:int = name.indexOf("[") + 1;
			var endIdx:int = name.indexOf("]");
			
			if (startIdx == -1 || endIdx == -1)
			{
				return null;
			}
			
			if (startIdx < endIdx)
			{
				return name.substring(startIdx, endIdx);
			}
			
			return null;
		}

		private function getChildren():void
		{
			if (!online)
			{
				logger.warn("schedule is offline");
				return;
			}
			_loadedChildren = true;
			_children.removeAll();
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "children", null, _children));
			
			var call:MediatorNodeCall = _node.execute("children_schedule_names", null);
			call.addCallback(handleGetChildrenNodesResult, handleGetChildrenNodesError);
		}		
		
		private function handleGetChildrenNodesResult(method:AsyncMethod, result:Object):void
		{
			_children.removeAll();
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "children", null, _children));
			
			logger.debug("handleGetChildrenNodesResult({0}, {1})", _node.path, result);
			for each (var nodeName:String in result)
			{
				var schedule:HierarchicalSchedule = new HierarchicalSchedule();
				
				schedule.initFromNode(this, _node.getService().getNode(_node.path + "/" + nodeName) as MediatorNode);
				
				_children.addItem(schedule);
			}
			
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "children", null, _children));
		}
		
		private function handleGetChildrenNodesError(method:MediatorNodeCall, error:Object):void
		{
			processException("Unable to get children: " + error, method, error);
			//throw new Error("Unable to get children for schedule('"+_node.path+"'): " + error);
		}
		
		/**
		 * Clears and resets all daily entries
		 */
		private function initializeDailyEntries():void
		{
			//_dailyEntries.removeAll();
			// purge daily entries
			for each (var entries:ArrayCollection in _dailyEntries)
			{
				entries.removeAll();
			}
			
			_exceptions.removeAll();
			properties.removeAll();
			
			
			for (var i:int = 0; i < DAY_INDEXES.length; i++)
			{
				var collection:ArrayCollection;
				
				if (i < _dailyEntries.length)
				{
					collection = _dailyEntries.getItemAt(i) as ArrayCollection;
					collection.removeAll();
				} 
				else
				{
					collection = new ArrayCollection();
					// add entry for daily collection
					_dailyEntries.addItem(collection);
				}
				
				var sort:Sort = new Sort();
				sort.fields = [ new SortField("time", false, false, true) ];
				collection.sort = sort;
				collection.refresh();
			}
		}	

		private function handleGetSummary(method:AsyncMethod, result:Object):void
		{
			//needUpdating = false;
			initializeDailyEntries();
			// Format is:
			if (result[1].length > 0)
			{
				parseDailyEntries(result[1][0][1], result[0]);
			}
			
			if (result[2].length > 0)
			{
				parseExceptions(result[2][0], result[0]);
			}
			
			updateDailyEntries();
			dispatchEvent(new ScheduleEvent(ScheduleEvent.SUMMARY_COMPLETE));
			
			getEventMeta();
		}
		
		private function parseDailyEntries(names:Array, entries:Array):void
		{
			// Convert the entries into  dictionary for easier access 
			var entryDict:Object = {};
			
			for each (var entry:Array in entries)
			{
				var name:String = entry[0] as String;
				
				if (entry.length > 1)
				{
					entryDict[name] = entry.slice(1);
				}
				else
				{
					entryDict[name] = [];
				}
			}
			
			for each (var name:String in names)
			{
				logger.debug("parsing daily entries for '{0}'", _node.path);
				var tempDailyEntries:Array = entryDict[name];
				
				for each (var entryArray:Array in tempDailyEntries)
				{
					logger.debug("\t" + entryArray);
					var dailyEntry:DailyEntry = DailyEntry.fromValues(entryArray[0], entryArray[1], entryArray[2]);
					addDailyEntry(name, dailyEntry);
				}
			}
		}
		
		/**
		 * Creates a daily entry with a proper event meta.  The rest is undefined. 
		 */
		public function createDailyEntry():DailyEntry
		{
			var entry:DailyEntry = new DailyEntry();
			
			if (metaData.length == 0)
			{
				createDefaultEventMeta();
			}
			
			
			var firstMetaEvent:EventMetaData = metaData.getItemAt(0) as EventMetaData;
			
			entry.eventMeta = firstMetaEvent;
			entry.updateFromMeta();
			
			return entry;
		}
		
		private function parseExceptions(entries:Array, dailyEntries:Array):void
		{
			logger.debug("Parsing exceptions: " + entries);
			/** Convert daily entries to object dictionary */
			var tempDailyEntries:Object = {};
			
			for each (var entry:Object in dailyEntries)
			{
				tempDailyEntries[entry[0]] = entry.slice(1);//entry[1];
			}
			
			if (entries.length > 2)
			{
				for (var i:int = 1; i < entries.length - 1; i++)
				{
					var exceptionVals:Array = entries[i];
					
					var exceptionEntry:ScheduleExceptionEntry = 
						ScheduleExceptionEntry.fromValues(this, exceptionVals,
							tempDailyEntries[exceptionVals[0]]);
					_exceptions.addItem(exceptionEntry);
				}
			}	
		}
		
		private function handleGetSummaryError(call:MediatorNodeCall, error:Object):void
		{
			logger.error("ERROR!:" + error);
			
			processException("Unable to get summary: " + error, call, error);
			
		}
		
		private function processException(message:String, call:MediatorNodeCall, error:Object):void
		{
			try
			{
				var exception:XML = new XML(call.result.faultString)
				
				if (exception["class"] == "socket.error" ||
					exception["class"] == "mpx.service.cloud.hosts.EResourceUnavailable" ||
					exception["class"] == "mpx.lib.exceptions.ERNATimeout" )
				{
					//trace("Looks like the schedule is offline!");
					
					setOnline(false);
					dispatchEvent(new Event(Event.COMPLETE)); // TODO Refactor
					return;
				}
				
			}
			catch (e:Error)
			{
				throw new Error("Error while getting summary and unable to parse faultString: " + e + ": " + error);
			}
			
			// FIXME: Temporary parsing of fault code
			// Need to dispatch callback error
			 
			throw new Error(message);
		}

		

		public function addDailyEntry(day:String, entry:DailyEntry):void
		{
			var index:int = DAY_INDEXES.indexOf(day);
			
			var entries:ArrayCollection = null;
			
			entries = _dailyEntries.getItemAt(index) as ArrayCollection;
			
			if (entries == null)
			{
				entries = new ArrayCollection();
				_dailyEntries.setItemAt(entries, index);
			}
			
			entries.addItem(entry);
			
			var event:ScheduleEvent = new ScheduleEvent(ScheduleEvent.DAILENTRY_UPDATED);
			event.item = entry;
			dispatchEvent(event);
		}
		
		public function removeChildSchedule(childSchedule:HierarchicalSchedule):void
		{
			var idx:int = _children.getItemIndex(childSchedule);
			
			if (idx != -1)
			{
				_children.removeItemAt(idx);
				childSchedule.parent = null;
				
				// TODO Make it more specific
				// RXC Was removed for testing
				// dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "children", null, _children)); 
			}
		}
		
		public function addChildSchedule(childSchedule:HierarchicalSchedule):void {
			if (_children.getItemIndex(childSchedule) == -1) {
				var oldParent:HierarchicalSchedule = childSchedule.parent;
				
				if (oldParent != null) {
					oldParent.removeChildSchedule(childSchedule);
				}
				// if it's a root, then it's the child of the manager =(
				else
				{
				//	throw new Error("Root schedule should be removed by manager");
				}
				
				// TODO Need to update the paths for all children/grandchildren
				childSchedule.parent = this;
				if (this.isRemote) {
					childSchedule._isRemote = this._isRemote;
				}
				
				fixDescendantsPath(this, childSchedule);
				_children.addItem(childSchedule);
				//dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "children", null, _children)); 
			}
		}
		
		/**
		 * Fixes the prefix path of the child to point to this schedule's path.
		 * 
		 * This usually happens if a schedule is moved and added to the child
		 * after it had been a child of another schedule. 
		 * 
		 * @param sched the start of the schedule to begin fixing paths from
		 */
		cisco_internal function fixDescendantsPath(parent:Object, sched:HierarchicalSchedule):void {
			var originalPath:String = /*original*/sched._node.path;
			var baseName:String = originalPath.substr(originalPath.lastIndexOf("/")+1);
			
			var destinationParentPath:String = parent._node.path;
			
			var newPath:String = destinationParentPath + "/" + baseName;
			
			sched._node.setPath(newPath);
			trace("new path: '"+newPath+"'");
			for each (var child:HierarchicalSchedule in sched._children) {
				fixDescendantsPath(sched, child);
			}
		}
		
		public function addException(entry:ScheduleExceptionEntry):void
		{
			_exceptions.addItem(entry);
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this,
				"exceptions", null, _exceptions));
				
			var event:ScheduleEvent = new ScheduleEvent(ScheduleEvent.EXCEPTIONS_UPDATED);
			event.item = entry;
			dispatchEvent(event);
		}
		
		public function removeException(entry:ScheduleExceptionEntry):void
		{
			var idx:int = _exceptions.getItemIndex(entry);
			
			if (idx != -1)
			{
				_exceptions.removeItemAt(idx);
			}
			
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this,
				"exceptions", null, _exceptions));
				
			var event:ScheduleEvent = new ScheduleEvent(ScheduleEvent.EXCEPTIONS_UPDATED);
			event.item = entry;
			dispatchEvent(event);
		}
		
		public function get exceptions():ArrayCollection
		{
			return _exceptions;
		}
	
		public function getEntriesForDay(day:String):ArrayCollection
		{
			var dayIndex:int = DAY_INDEXES.indexOf(day);
			
			if (dayIndex < 0)
			{
				return null;
			}
			
			
			//ensureDailyEntriesInitialized();
			
			return _dailyEntries[dayIndex];
		}	
		
		public function get dailyEntries():ArrayCollection
		{
			return _dailyEntries;
		}
		
		/**
		 * Retrieves the list of schedule names and only adds those that are new
		 */
		cisco_internal function updateSchedules():void {
			var call:MediatorNodeCall = _node.execute("children_schedule_names", null);
			call.addCallback(handleUpdateNamesResult, handleUpdateNamesError);
		}
		
		private function handleUpdateNamesResult(method:MediatorNodeCall, result:Object):void {
			logger.debug("update names result: " + result);
			
			var names:Array = result as Array;
			
			var found:Boolean = false;
			for each (var name:String in names) {
				found = false;
				for each (var sched:HierarchicalSchedule in this._children) {
					if (sched.name == name) {
						found = true;
						break;
					} 
				}
				
				if (found) {
					continue;
				}
				var schedule:HierarchicalSchedule = new HierarchicalSchedule();
				schedule.initFromNode(null,  _node.getService().getNode(_node.path + "/" + name) as MediatorNode);
				
				_children.addItem(schedule);
			}
		}
		
		private function handleUpdateNamesError(method:MediatorNodeCall, error:Object):void {
			throw new Error("Unable to update root schedules after modification");
		}
		
		
		override public function toString():String {
			return "HierarchicalSchedule(name='"+name+"')";
		}
	}
}