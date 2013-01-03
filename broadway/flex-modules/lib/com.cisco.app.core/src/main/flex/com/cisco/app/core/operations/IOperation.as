///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.operations
{
	import com.cisco.app.core.IDisposable;
	
	import flash.events.IEventDispatcher;

	public interface IOperation extends IDisposable, IEventDispatcher
	{
		function execute(monitor:IProgressMonitor, info:Object=null):void;
		
		function canExecute():Boolean;
		
		function cancel():void;
		
		function get cancelable():Boolean;
		
		function get label():String;
		
		function set label(value:String):void;
		
		function get isAsync():Boolean;
	}
}