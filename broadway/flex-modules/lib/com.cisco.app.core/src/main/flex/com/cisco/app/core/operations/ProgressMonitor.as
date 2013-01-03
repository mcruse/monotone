///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.operations
{
	import flash.events.Event;
	import flash.events.EventDispatcher;
	import flash.events.ProgressEvent;
	
	import mx.events.PropertyChangeEvent;

	[Event(name="done", type="com.cisco.app.core.operations.ProgressMonitorEvent")]
	[Event(name="canceled", type="com.cisco.app.core.operations.ProgressMonitorEvent")]
	[Event(name="work", type="com.cisco.app.core.operations.ProgressMonitorEvent")]
	[Event(name="taskNameChange", type="com.cisco.app.core.operations.ProgressMonitorEvent")]
	[Event(name="totalWorkChange", type="com.cisco.app.core.operations.ProgressMonitorEvent")]

	[Event(name="progress", type="flash.events.ProgressEvent")]
	[Event(name="complete", type="flash.events.Event")]
	
	public class ProgressMonitor extends EventDispatcher implements IProgressMonitor
	{
		private var _canceled:Boolean = false;
		
		private var _name:String;
		
		private var _taskName:String = "";
		
		private var _totalWork:int = 0;
		
		private var _currentWork:int = 0;
		
		public var bytesLoaded:int = 0;
		
		public var bytesTotal:int = 0; // For use by others who want the progress event
		
		public function ProgressMonitor()
		{
			super();
		}
		
		public function beginTask(name:String, totalWork:uint):void
		{
			taskName = name; // TODO Break up into main name and subtask names
			this.totalWork = totalWork;
			_currentWork = 0;
			bytesLoaded = 0;
			dispatchProgressEvent();
		}
		
		public function get totalWork():int
		{
			return _totalWork;
		}
		
		public function set totalWork(value:int):void
		{
			trace("total work: " + value);
			if (value != _totalWork)
			{
				var oldValue:int = _totalWork;
				_totalWork = value;
				bytesTotal = value;
				
				var event:ProgressMonitorEvent = new ProgressMonitorEvent(ProgressMonitorEvent.TOTAL_WORK_CHANGE);
				dispatchEvent(event);
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "bytesLoaded", oldValue, _totalWork));
			}
		}
		
		public function work(amount:uint):void
		{
			trace("work: " + amount);
			if (amount == 0)
			{
				return;
			}
			
			var oldValue:int = _currentWork;
			
			_currentWork += amount;
			
			bytesLoaded = _currentWork;
			
			var event:ProgressMonitorEvent = new ProgressMonitorEvent(ProgressMonitorEvent.WORK);
			dispatchEvent(event);
			
			dispatchProgressEvent();
		}
		
		private function dispatchProgressEvent():void
		{
			var progressEvent:ProgressEvent = new ProgressEvent(ProgressEvent.PROGRESS, false, false, bytesLoaded, bytesTotal);
			dispatchEvent(progressEvent);
		}
		
		public function done():void
		{
			dispatchEvent(new ProgressMonitorEvent(ProgressMonitorEvent.DONE));
			dispatchEvent(new Event(Event.COMPLETE));
		}
		
		public function get canceled():Boolean
		{
			return _canceled;
		}
		
		public function set canceled(value:Boolean):void
		{
			if (value != _canceled)
			{
				var oldValue:Boolean = _canceled;
				_canceled = value;
				
				var event:ProgressMonitorEvent = new ProgressMonitorEvent(ProgressMonitorEvent.CANCELED);
				dispatchEvent(event);
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "canceled", oldValue, _canceled));
				
			}
		}
		
		public function get taskName():String
		{
			return _taskName;
		}
		
		public function set taskName(value:String):void
		{
			if (value !== _taskName)
			{
				var oldValue:String = _taskName;
				_taskName = value;
				var event:ProgressMonitorEvent = new ProgressMonitorEvent(ProgressMonitorEvent.TASK_NAME_CHANGE);
				event.taskName = _taskName;
				dispatchEvent(event);
			}
		}
		
	}
}