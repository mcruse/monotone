package com.cisco.nbm.scheduler.ui.jobs
{
	import com.cisco.app.core.async.AsyncMethod;
	import com.cisco.app.core.jobs.Job;
	import com.cisco.app.core.operations.IProgressMonitor;
	import com.cisco.nbm.scheduler.HierarchicalScheduleManager;
	import com.cisco.nbm.scheduler.ScheduleDocument;
	import com.cisco.nbm.scheduler.ui.components.ConfirmSavePopup;
	import com.cisco.ui.components.DialogCloseReason;
	
	import flash.display.DisplayObject;
	
	import mx.controls.Alert;
	import mx.events.CloseEvent;

	public class ConfirmSaveScheduleJob extends Job
	{
		public var label:String;
		
		public var document:ScheduleDocument;
		
		public var displayObject:DisplayObject;
		
		//public var runOnClean:Job;
		
		private var confirmSavePopup:ConfirmSavePopup; 
		
		private var manager:HierarchicalScheduleManager;
		
		public var reason:String;
		
		private var monitor:IProgressMonitor;
		
		public function ConfirmSaveScheduleJob(label:String, document:ScheduleDocument, displayObject:DisplayObject,
			manager:HierarchicalScheduleManager)
		{
			super();
			this.label = label;
			this.document = document;
			this.displayObject = displayObject;
			this.manager = manager;
		}
		
		override public function run(monitor:IProgressMonitor):void
		{
			
			//runOnClean.addCallback(handleRunComplete, handleRunFail);
			
			if (!document.dirty)
			{
				//runOnClean.run(monitor); // call internal funcs
				reason = DialogCloseReason.OK;
				handleComplete();
				return;
			}
			
			this.monitor = monitor;
			// Must ask to save and then run
			//confirmSavePopup = PopUpManager.createPopUp(displayObject, ConfirmSavePopup, true) as ConfirmSavePopup;
			//PopUpManager.centerPopUp(confirmSavePopup);
			
			//confirmSavePopup.actionName = label;
			//confirmSavePopup.scheduleName = document.schedule.name;
			
			/*
			confirmSavePopup = ConfirmSavePopup.show(label, document.schedule.name, null, 
				handleConfirmSaveClose);
			*/
			var text:String = "The schedule " + document.schedule.name + " has been modified.\n" + 
				"Click Yes to save it,\nClick No to discard the changes,\nor click Cancel to return to " +
				"editing the schedule";
				
			var alert:Alert = Alert.show(text, "Schedule Modified", Alert.YES | Alert.NO | Alert.CANCEL,
				null, handleConfirmSaveClose, null, Alert.CANCEL);
			
			//confirmSavePopup.addEventListener(Event.COMPLETE, handleConfirmSaveComplete);
		}
	
		private function handleConfirmSaveClose(event:CloseEvent):void
		{
			if (event.detail == Alert.YES)
			{
				reason = DialogCloseReason.OK;
				runSaveScheduleJob();
			}
			
			else if (event.detail == Alert.NO)
			{
				reason = DialogCloseReason.OK;
				handleComplete();
			}
			else if (event.detail == Alert.CANCEL)
			{
				reason = DialogCloseReason.CANCEL;
				handleComplete();
			}
			/*
			var closeReason:String = confirmSavePopup.reason;
			
			confirmSavePopup.removeEventListener(Event.COMPLETE, handleConfirmSaveComplete);
			PopUpManager.removePopUp(confirmSavePopup);
			
			confirmSavePopup = null;
			
			if (closeReason == DialogCloseReason.CANCEL)
			{
				reason = DialogCloseReason.CANCEL;
				handleComplete();
			}
			else
			{
				// ok, now we attempt the save
				runSaveScheduleJob();
			}
			*/
		}
		
		private function runSaveScheduleJob():void
		{
			
			var job:Job = manager.save(document.schedule);
			job.addCallback(handleSaveComplete, handleSaveError);
			job.run(this.monitor);
			
		}
		
		private function handleSaveComplete(method:AsyncMethod, result:Object):void
		{
			reason = DialogCloseReason.OK;
			handleComplete();
		}
		
		private function handleSaveError(method:AsyncMethod, result:Object):void
		{
			reason = DialogCloseReason.OK;
			setError(result);
			dispatchError();
		}
		
		private function handleRunComplete(method:AsyncMethod, result:Object):void
		{
			reason = DialogCloseReason.OK;
			
			handleComplete();
		}
		
		private function handleRunFail(method:AsyncMethod, error:Object):void
		{
			setError(error);
			dispatchError();
		}
		
		override protected function cleanup():void
		{
			this.monitor = null;
			this.document = null;
			this.displayObject =  null;
			this.manager = null;
		//	this.runOnClean = null;
		}
	}
}