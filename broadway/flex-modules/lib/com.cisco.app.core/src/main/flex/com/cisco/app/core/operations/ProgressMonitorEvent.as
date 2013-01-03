///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.operations
{
	import flash.events.Event;

	public class ProgressMonitorEvent extends Event
	{
		public static const BEGIN_TASK:String = "beginTask"
		
		public static const WORK:String = "work";
		
		public static const CANCELED:String = "canceled";
		
		public static const TASK_NAME_CHANGE:String = "taskNameChange";
		
		public static const TOTAL_WORK_CHANGE:String = "totalWorkChange";
		
		public static const DONE:String = "done";
		
		public var taskName:String;
		
		public var totalWork:int;
		
		public var work:int
		
		public function ProgressMonitorEvent(type:String, bubbles:Boolean=false, cancelable:Boolean=false)
		{
			super(type, bubbles, cancelable);
		}
		
	
		/**
		 * function beginTask(name:String, totalWork:uint):void;
		
		function work(amount:uint):void;
		
		function done():void;
		
		function get canceled():Boolean;
		
		function set canceled(value:Boolean):void;
		
		function get taskName():String;
		
		function set taskName(value:String):void;*/	
	}
}