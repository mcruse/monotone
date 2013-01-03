package com.cisco.nbm.scheduler.ui.components
{
	import com.cisco.app.core.operations.ProgressMonitor;
	import com.cisco.app.core.operations.ProgressMonitorEvent;
	
	import flash.display.DisplayObject;
	import flash.display.Sprite;
	import flash.events.EventPhase;
	
	import mx.core.Application;
	import mx.core.IFlexDisplayObject;
	import mx.events.FlexEvent;
	import mx.managers.ISystemManager;
	import mx.managers.PopUpManager;
	
	[Event(name="cancel", type="flash.events.Event")]
	
	[Event(name="complete", type="flash.events.Event")]
	
	public class ProgressPopup extends ProgressPopupBase
	{
		public var monitor:ProgressMonitor;
		
		private var _text:String;
		
		public function ProgressPopup()
		{
			super();
			
			monitor = new ProgressMonitor();
			monitor.addEventListener(ProgressMonitorEvent.TASK_NAME_CHANGE, handleTaskNameChange);
			monitor.addEventListener(ProgressMonitorEvent.TOTAL_WORK_CHANGE, handleTotalWorkChange);
		}
		
		override protected function init():void
		{
			super.init();
			
			
			progressBar.source = monitor;
					
			updateControls();
		}
		
		protected function updateControls():void
		{
			progressBar.label = _text;
			
			//if (monitor
		}
		
		public function handleTaskNameChange(event:ProgressMonitorEvent):void
		{
			text = event.taskName;
		}

		public function handleTotalWorkChange(event:ProgressMonitorEvent):void
		{
			updateControls();
		}

		
		public function set text(value:String):void
		{
			_text = value;
			
			if (initialized)
			{
				progressBar.label = value;
			}
		}

		override public function destroy():void
		{
			super.destroy();
			
			if (initialized)
			{
				progressBar.source = null;
			}
			_text = null;
			
			monitor.removeEventListener(ProgressMonitorEvent.TASK_NAME_CHANGE, handleTaskNameChange);
			monitor = null
		}
		
		public static function show(panelParent:DisplayObject=null):ProgressPopup
		{
			var panel:ProgressPopup;
			
			if (panelParent == null)
			{
				var sm:ISystemManager = ISystemManager(Application.application.systemManager);
				
	            if (sm.useSWFBridge())
	                panelParent = Sprite(sm.getSandboxRoot());
	            else
	                panelParent = Sprite(Application.application);
   			}
   			
   			panel = new ProgressPopup();
   			
   			panel.setActualSize(panel.getExplicitOrMeasuredWidth(),
                        panel.getExplicitOrMeasuredHeight());
			
			
			panel.addEventListener(FlexEvent.CREATION_COMPLETE, static_creationComplete);
			
			PopUpManager.addPopUp(panel, panelParent, true);
   			
   			return panel;   
		}
		
		private static function static_creationComplete(event:FlexEvent):void
		{
			if (event.target is IFlexDisplayObject && event.eventPhase == EventPhase.AT_TARGET)
	        {
	            event.target.removeEventListener(FlexEvent.CREATION_COMPLETE, static_creationComplete);
	            PopUpManager.centerPopUp(IFlexDisplayObject(event.target));
	        }
		}
	}
}