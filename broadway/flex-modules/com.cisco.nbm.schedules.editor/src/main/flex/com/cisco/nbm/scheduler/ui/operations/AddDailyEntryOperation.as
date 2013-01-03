package com.cisco.nbm.scheduler.ui.operations
{
	import com.cisco.app.core.operations.AbstractUndoableOperation;
	import com.cisco.app.core.operations.IProgressMonitor;
	import com.cisco.nbm.scheduler.DailyEntry;
	import com.cisco.nbm.scheduler.ScheduleDocument;
	
	import mx.logging.ILogger;
	import mx.logging.Log;

	public class AddDailyEntryOperation extends AbstractUndoableOperation
	{
		private var day:String;
		
		private var entry:DailyEntry;
		
		//private var schedule:HierarchicalSchedule;
		private var document:ScheduleDocument;
		
		private static const logger:ILogger = Log.getLogger("cisco.nbm.scheduler.operations.AddDailyEntryOperation");
		
		private var wasDirty:Boolean = false;
		
		public function AddDailyEntryOperation(
			document:ScheduleDocument,
			day:String, entry:DailyEntry) 
		{
			super("Add Entry to " + day);
			
			this.day = day;
			this.entry = entry;
			//this.schedule = schedule;
			this.document = document;
			wasDirty = this.document.dirty;
		}
		
		override public function execute(monitor:IProgressMonitor, info:Object=null):void
		{
			internalExecute(monitor);
		}
		
		private function internalExecute(monitor:IProgressMonitor):void
		{
			//var collection:ArrayCollection = schedule.getEntriesForDay(name);
			
			document.addDailyEntry(day, entry);
		}
		
		override public function undo(monitor:IProgressMonitor):void
		{
			document.dirty = wasDirty;
			document.schedule.removeDailyEntry(day, entry);
		}
		
		override public function redo(monitor:IProgressMonitor):void
		{
			internalExecute(monitor);
		}
		
		override public function dispose():void
		{
			this.entry = null;
			this.document = null;
		}
	}
}