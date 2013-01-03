package com.cisco.nbm.scheduler.ui.jobs
{
	import com.cisco.app.core.async.AsyncMethod;
	import com.cisco.app.core.jobs.Job;
	import com.cisco.app.core.operations.IProgressMonitor;
	import com.cisco.nbm.scheduler.HierarchicalSchedule;
	import com.cisco.nbm.scheduler.HierarchicalScheduleManager;

	public class AddScheduleJob extends Job
	{
		private var manager:HierarchicalScheduleManager;
		private var parentSchedule:HierarchicalSchedule;
		private var newName:String;
		
		public function AddScheduleJob(manager:HierarchicalScheduleManager, 
			parentSchedule:HierarchicalSchedule, newName:String)
		{
			super();
			this.manager = manager;
			this.parentSchedule = parentSchedule;
			this.newName = newName;
		}
		
		override public function run(monitor:IProgressMonitor):void
		{
			var job:AsyncMethod = manager.createSchedule(parentSchedule, newName);
		}
		
		private function handleResult(method:AsyncMethod, result:Object):void
		{
		}
		
		private function handleFail(method:AsyncMethod, error:Object):void
		{
		}
	}
}