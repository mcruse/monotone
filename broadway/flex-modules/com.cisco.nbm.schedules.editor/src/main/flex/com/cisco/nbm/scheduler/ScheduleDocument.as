package com.cisco.nbm.scheduler
{
	import com.cisco.nbm.scheduler.events.ScheduleEvent;
	import com.cisco.nbm.scheduler.ui.ScheduleDocumentEvent;
	
	import flash.events.Event;
	import flash.events.EventDispatcher;
	
	import mx.events.PropertyChangeEvent;
	import mx.logging.ILogger;
	import mx.logging.Log;
	
	[Event(name="scheduleChange", type="com.cisco.nbm.schedule.ui.ScheduleDocumentEvent")]
	[Event(name="scheduleModified", type="com.cisco.nbm.schedule.ui.ScheduleDocumentEvent")]
	
	
	/**
	 * Document class used for managing a selected schedule.
	 * 
	 * This class is passed to the editors and command
	 * managers.  These, in turn, will manipulate the schedule
	 * by making changes to the document.
	 * 
	 * Most modifications should happen through this class.  As
	 * it is currently implemented, modifications are made
	 * directly to the schedule.  
	 * 
	 * The reason for manipulating the document instead of the 
	 * schedule is that the document can keep track of the 
	 * modified state of the document instead of relegating that
	 * duty to the individual editors.
	 */
	public class ScheduleDocument extends EventDispatcher
	{
		public var _dirty:Boolean;
		
		private var _schedule:HierarchicalSchedule;
		
		private var logger:ILogger = Log.getLogger("cisco.nbm.scheduler.ScheduleDocument");
		
		public function ScheduleDocument()
		{
		}
	
		//-------------------------------------------------
		// Public functions
		//-------------------------------------------------
	
		/**	
		 * The save function will save the schedule.
		 * 
		 * It is currently not implemented.
		 */
		public function save():void
		{
			
		}
		
		//-------------------------------------------------
		// Property getters - setters
		//-------------------------------------------------
		
		/**		
		 * Flag indicating the modified state of the document.
		 */
		[Bindable]
		public function set dirty(value:Boolean):void
		{
			logger.debug("schedule document set dirty: {0}", value);
			if (value != _dirty)
			{
				var oldValue:Boolean = _dirty;
				_dirty = value;
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "dirty", oldValue, value));
			}
		}
		
		/** 
		 * Flag indicating the modified state of the document. 
		 */
		public function get dirty():Boolean
		{
			return _dirty;
		}
		
		/**
		 * The schedule that this document is managing.
		 * 
		 * It registers listeners to the schedule so destroy
		 * must be called at the end of the lifecycle
		 * so that all listeners are removed.
		 */
		public function setSchedule(value:HierarchicalSchedule):void
		{
			if (_schedule !== value)
			{
				if (_schedule != null)
				{
					// This doesn't work with trying to identify if a 
					// schedule has returned to its initial state 
					// because we'd have to keep track of the initial
					// schedule state.  Therefore, all changes must
					// be performed via the document and the document 
					// must keep track of the history.
					_schedule.removeEventListener(PropertyChangeEvent.PROPERTY_CHANGE,
						handleSchedulePropertyChange);
					_schedule.removeEventListener(ScheduleEvent.DAILENTRY_UPDATED,
							handleMetaChange);
					_schedule.removeEventListener(ScheduleEvent.EXCEPTIONS_UPDATED,
						handleMetaChange);
					_schedule.removeEventListener(ScheduleEvent.METADATA_UPDATED,
						handleMetaChange);
					_schedule.removeEventListener(ScheduleEvent.PROPERTY_UPDATED,
						handleMetaChange);
				}
				
				var oldValue:HierarchicalSchedule = _schedule;
				_schedule = value;
				
				if (_schedule != null)
				{
					if (!_schedule.initialized)
					{
						_schedule.initialize();
					}
					
					_schedule.addEventListener(PropertyChangeEvent.PROPERTY_CHANGE,
						handleSchedulePropertyChange);
					_schedule.addEventListener(ScheduleEvent.DAILENTRY_UPDATED,
						handleMetaChange);
					_schedule.addEventListener(ScheduleEvent.EXCEPTIONS_UPDATED,
						handleMetaChange);
					_schedule.addEventListener(ScheduleEvent.METADATA_UPDATED,
						handleMetaChange);
					_schedule.addEventListener(ScheduleEvent.PROPERTY_UPDATED,
						handleMetaChange);
				}
				
				var event:ScheduleDocumentEvent = new ScheduleDocumentEvent(ScheduleDocumentEvent.SCHEDULE_CHANGE);
				event.document = this;
				
				dirty = false;
				
				dispatchEvent(event);
			}
		}
		
		/**
		 * This updated the dirty entry to true if the schedule 
		 * it was managing changed.  But, all changes should occur
		 * through the document and not through the schedule.  
		 */
		private function handleMetaChange(event:Event):void
		{
			logger.warn("**** HANDLE META CHANGE! NOT HANDLED!!!");
			if (!_schedule.initialized)
			{
				return;
			}
			
			//dirty = true;
		}
		
		public function get schedule():HierarchicalSchedule
		{
			return _schedule;
		}
		
		//-------------------------------------------------
		// EVENT HANDLERS
		//-------------------------------------------------
		
		/*
		 * Dispatches a ScheduleModified event.
		 */
		private function handleSchedulePropertyChange(event:PropertyChangeEvent):void
		{
			logger.debug("handleSchedulePropertyChange({0}); property={1}", event, event.property);
			
			logger.debug("Schedule Initialized: {0}", _schedule.initialized);
			
			if (!_schedule.initialized)
			{
				return;
			}
			
			var newEvent:ScheduleDocumentEvent = 
				new ScheduleDocumentEvent(ScheduleDocumentEvent.SCHEDULE_MODIFIED);
			newEvent.document = this;
			dispatchEvent(newEvent);
		}
		
		public function addDailyEntry(day:String, entry:DailyEntry):void
		{
			logger.debug("addDailyEntry('{0}', '{1}')", day, entry);
			_schedule.addDailyEntry(day, entry);
			dirty = true;
		}
		
		public function removeDailyEntry(day:String, entry:DailyEntry):void
		{
			_schedule.removeDailyEntry(day, entry);
		}
		
		public function updateMetaEntry(metaEntry:EventMetaData, 
			newName:String, newColor:int, newValue:String):void
		{
			_schedule.updateMetaEntry(metaEntry, newName, newColor, newValue);
			dirty = true;
		}
		
		
		public function addMetaDataItem(newMeta:EventMetaData):void
		{
			logger.debug("addMetaDataItem({0})", newMeta);
			_schedule.metaData.addItem(newMeta);
			dirty = true;
		}
		
		public function deleteEventMetaEntry(meta:EventMetaData):void
		{
			_schedule.deleteEventMetaEntry(meta);
			dirty = true;
		}
		
		public function moveMetaData(sourceIdx:int,  destIdx:int):void
		{
			_schedule.moveMetaData(sourceIdx, destIdx);
			dirty = true;
		}
		
		public function addException(entry:ScheduleExceptionEntry):void
		{
			_schedule.addException(entry);
			dirty = true;
		}
		
		public function removeException(entry:ScheduleExceptionEntry):void
		{
			_schedule.removeException(entry);
			dirty = true;
		}
		
		public function modifyExceptionEntry(entry:ScheduleExceptionEntry,
			newName:String, startDate:Date, endDate:Date):void
		{
			entry.name = newName;
			entry.startDate = startDate;
			entry.endDate = endDate;
			
			dirty = true;
		}
		
		public function addExceptionDailyEntry(exceptionEntry:ScheduleExceptionEntry):DailyEntry
		{
			var entry:DailyEntry = exceptionEntry.createDailyEntry();
			exceptionEntry.addDailyEntry(entry);
			dirty = true;
			return entry;
		}
		
		public function removeExceptionDailyEntry(exceptionEntry:ScheduleExceptionEntry,
			dailyEntry:DailyEntry):void
		{
			exceptionEntry.removeDailyEntry(dailyEntry);
			
			dirty = true
		}
	}
}