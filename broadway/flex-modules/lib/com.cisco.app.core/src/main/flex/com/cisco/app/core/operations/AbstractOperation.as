///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.operations
{
	import flash.events.ErrorEvent;
	import flash.events.Event;
	import flash.events.EventDispatcher;
	
	[Event(name="complete", type="flash.events.Event")]
	[Event(name="error", type="flash.events.ErrorEvent")]
	
	public class AbstractOperation extends EventDispatcher implements IOperation
	{
		private var _label:String;
				
		public function AbstractOperation(label:String)
		{
			_label = label;
			//trace("(((((create op: " + _label);
		}

		public function dispose():void
		{
			//trace(")))))dispose: " + _label);
		}
		
		public function execute(monitor:IProgressMonitor, info:Object=null):void
		{
			throw new Error("execute must be implemented");
		}
		
		public function canExecute():Boolean
		{
			return false;
		}
		
		public function cancel():void
		{
		}
		
		public function get cancelable():Boolean
		{
			return false;
		}
		
		public function get label():String
		{
			return _label;
		}
		
		public function set label(value:String):void
		{
			_label = label;
		}
		
		public function get isAsync():Boolean
		{
			return false;
		}
		
		protected function dispatchComplete():void
		{
			dispatchEvent(new Event(Event.COMPLETE));
		}
		
		protected function dispatchError(text:String):void
		{
			var event:ErrorEvent = new ErrorEvent(ErrorEvent.ERROR, false, false, text);
			dispatchEvent(event);
		}
		
		protected function dispatchCancel():void
		{
			var event:Event = new Event(Event.CANCEL);
			dispatchEvent(event);
		}
	}
}
