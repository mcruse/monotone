package com.cisco.nbm.scheduler.ui.operations
{
	import com.cisco.app.core.jobs.Job;
	import com.cisco.app.core.operations.IProgressMonitor;
	import com.cisco.nbm.scheduler.HierarchicalSchedule;
	import com.cisco.nbm.scheduler.HierarchicalScheduleManager;

	public class MoveScheduleOperation extends Job
	{
		
		private var originalParent:HierarchicalSchedule;
		
		private var newParent:HierarchicalSchedule;
		
		private var movedItem:HierarchicalSchedule;
		
		private var manager:HierarchicalScheduleManager;
		
		public function MoveScheduleOperation(manager:HierarchicalScheduleManager,
			sourceSchedule:HierarchicalSchedule, newParent:HierarchicalSchedule)
		{
			originalParent = sourceSchedule.parent;
			
			
			this.newParent = newParent;
			this.manager = manager;
			this.movedItem = sourceSchedule;
		}
		
		override public function run(monitor:IProgressMonitor):void
		{
			manager.move(movedItem, newParent);
		}
		
		override public function dispose():void
		{
			this.originalParent = null;
			this.newParent = null;
			this.movedItem = null;
			this.manager = null;
		}
	}
}