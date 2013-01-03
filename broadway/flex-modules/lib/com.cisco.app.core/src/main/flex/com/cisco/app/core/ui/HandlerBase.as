///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.ui
{
	import flash.events.EventDispatcher;
	import flash.events.IEventDispatcher;
	
	import mx.events.PropertyChangeEvent;

	public class HandlerBase extends EventDispatcher implements IHandler
	{
		private var _enabled:Boolean = true;
		
		public function HandlerBase(target:IEventDispatcher=null)
		{
			super(target);
		}
		
		public function execute(executionEvent:ExecutionEvent):Object
		{
			throw new Error("You must implement execute");
		}
		
		public function dispose():void
		{
			enabled = false;
		}
		
		public function get enabled():Boolean
		{
			return _enabled;
		}
		
		public function set enabled(value:Boolean):void
		{
			var oldValue:Boolean = _enabled;
			_enabled = value;
			
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "enabled", oldValue, _enabled));
		}
		
		public function get handled():Boolean
		{
			return true; // Need to update with an expression
		}
		
		public function set handled(value:Boolean):void
		{
		}
		
		
		
	}
}