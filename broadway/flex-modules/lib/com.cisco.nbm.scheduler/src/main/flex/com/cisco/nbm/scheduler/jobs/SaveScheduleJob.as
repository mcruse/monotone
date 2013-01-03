package com.cisco.nbm.scheduler.jobs
{
	import com.cisco.app.core.async.AsyncMethod;
	import com.cisco.app.core.jobs.Job;
	import com.cisco.app.core.operations.IProgressMonitor;
	import com.cisco.cisco_internal;
	import com.cisco.nbm.scheduler.HierarchicalSchedule;
	import com.cisco.nbm.scheduler.HierarchicalScheduleManager;
	import com.cisco.nbm.xmlrpc.v2.MediatorNodeCall;
	
	public class SaveScheduleJob extends Job
	{
		private var schedule:HierarchicalSchedule;
		
		private var manager:HierarchicalScheduleManager;
		
		private var monitor:IProgressMonitor;
		
		public function SaveScheduleJob(schedule:HierarchicalSchedule,
			manager:HierarchicalScheduleManager)
		{
			super();
			
			this.schedule = schedule;
			this.manager =  manager;
		}
		
		override public function run(monitor:IProgressMonitor):void
		{
			this.monitor = monitor;
			
			if (monitor != null)
			{
				monitor.beginTask(
					"Saving schedule '" + schedule.name + "'", 3);
			}
			
			updateEventMeta();
		}
		
		private function saveSummary():void
		{
			
			var summary:Array = schedule.toSummary();
			schedule.markChildrenNeedUpdating(true);
			var call:MediatorNodeCall = manager.cisco_internal::_node.execute("set_summary", 
				[ schedule._node.path,
					summary ]);
					
			call.addCallback(handleSetSummaryComplete, handleSetSummaryError);	
		}
		
		private function updateEventMeta():void
		{
			
			var call:MediatorNodeCall = schedule.updateEventMeta();
			
			call.addCallback(handleUpdateEventMetaComplete, handleUpdateEventMetaError);
		}
		
		private function handleSetSummaryComplete(method:AsyncMethod, result:Object):void
		{
			if (monitor != null)
			{
				monitor.work(1);
			}
			
			done();
		}
		
		
		private function handleUpdateEventMetaComplete(method:AsyncMethod, result:Object):void
		{
			if (monitor != null)
			{
				monitor.work(1);
			}
			
			var call:MediatorNodeCall = schedule.updateProperties();
			call.addCallback(handleUpdatePropertiesComplete, handleUpdatePropertiesError);
		}

		private function handleUpdatePropertiesComplete(method:AsyncMethod, result:Object):void
		{
			if (monitor != null)
			{
				monitor.work(1);
			}
			
			saveSummary();
		}
		
		private function done():void
		{
			monitor = null;
			handleComplete();
		}
		
		private function handleUpdatePropertiesError(method:AsyncMethod, error:Object):void
		{
			setError("Unable to update properties: " + error);
			dispatchError();
		}
		
		private function handleUpdateEventMetaError(method:AsyncMethod, error:Object):void
		{
			setError("Unable to update schedule event meta data: " + error);
			dispatchError();
		}
		
		private function handleSetSummaryError(method:AsyncMethod, error:Object):void
		{
			setError("Unable to save schedule: " + error);
			dispatchError();
		}
	}
}