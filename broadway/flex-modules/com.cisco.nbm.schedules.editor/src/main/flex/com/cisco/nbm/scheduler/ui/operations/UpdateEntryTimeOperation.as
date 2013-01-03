package com.cisco.nbm.scheduler.ui.operations
{
	import com.cisco.app.core.operations.AbstractUndoableOperation;
	import com.cisco.app.core.operations.IProgressMonitor;
	import com.cisco.nbm.scheduler.DailyEntry;
	import com.cisco.nbm.scheduler.EventMetaData;
	import com.cisco.nbm.scheduler.ScheduleDocument;

	public class UpdateEntryTimeOperation extends AbstractUndoableOperation
	{
		public var originalTime:int = -1;
		
		public var entry:DailyEntry;
		
		public var hours24:int;
		
		public var minutes:int;
		
		public var newTime:int = -1;
		//public var newTime:int = -1;
		
		public var meta:EventMetaData;
		
		public var rawValue:String;
		
//		public var originalMetaValue:Object;
		public var originalMeta:EventMetaData;
		
		private var scheduleDocument:ScheduleDocument;
		
		private var wasDirty:Boolean = false;
		
		public function UpdateEntryTimeOperation(entry:DailyEntry, hours24:int, minutes:int,
			scheduleDocument:ScheduleDocument,
			time:int=-1, meta:EventMetaData=null, rawValue:String=null
			)
		{
			super("Set time");
			this.meta = meta;
			this.entry = entry;
			this.originalTime = entry.time;
			//this.originalMetaValue = entry.value;
			this.originalMeta = entry.eventMeta;
			this.hours24 = hours24;
			this.minutes = minutes;
			this.scheduleDocument = scheduleDocument;
			this.rawValue = rawValue;	
			wasDirty = scheduleDocument.dirty;
			
			newTime = time;
		}
		
		override public function execute(monitor:IProgressMonitor, info:Object=null):void
		{
			internalExecute(monitor);
		}
		
		private function internalExecute(monitor:IProgressMonitor):void
		{
			if (newTime == -1)
			{
				entry.hours = hours24;
				entry.minutes = minutes;
			}
			else
			{
				entry.time = newTime;
			}
			
			if (meta != null)
			{
				entry.eventMeta = meta;
				entry.updateFromMeta();
			}
			
			if (rawValue != null) {
				entry.eventMeta = null;
				entry.value = rawValue;
			}
			
			scheduleDocument.dirty = true;
		} 
		
		override public function undo(monitor:IProgressMonitor):void
		{
			entry.time = originalTime;
			entry.eventMeta = originalMeta;
			
			// Set schedule document not dirty anymore
			scheduleDocument.dirty = wasDirty;
		}
		
		override public function redo(monitor:IProgressMonitor):void
		{
			internalExecute(monitor);
		}
		
		override public function dispose():void
		{
			this.entry = null;
			this.scheduleDocument = null;
			this.meta = null;
			this.originalMeta = null;
		}
	}
}