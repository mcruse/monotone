package com.cisco.nbm.scheduler.ui.operations
{
	import com.cisco.app.core.operations.AbstractUndoableOperation;
	import com.cisco.app.core.operations.IProgressMonitor;
	import com.cisco.nbm.scheduler.DailyEntry;
	import com.cisco.nbm.scheduler.ScheduleDocument;

	public class RemoveDailyEntryOperation extends AbstractUndoableOperation
	{
		private var day:String;
		
		private var entry:DailyEntry;
		
		private var document:ScheduleDocument;
		
		private var wasDirty:Boolean = false;
		
		public function RemoveDailyEntryOperation(document:ScheduleDocument,
			day:String, entry:DailyEntry) 
		{
			super("Remove Entry for " + day);
			
			this.day = day;
			this.entry = entry;
			this.document = document;
			wasDirty = this.document.dirty;
		}
		
		override public function execute(monitor:IProgressMonitor, info:Object=null):void
		{
			internalExecute(monitor);
		}
		
		private function internalExecute(monitor:IProgressMonitor):void
		{
			document.removeDailyEntry(day, entry);
			document.dirty = true;
		}
		
		override public function undo(monitor:IProgressMonitor):void
		{
			//document.schedule.addDailyEntry(day, entry);
			document.addDailyEntry(day, entry);
			document.dirty = wasDirty;
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