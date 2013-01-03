///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.ui
{
	import com.cisco.app.core.IDisposable;
	
	import flash.events.IEventDispatcher;
	
	/**
	 * 
	 * @author Robert Cadena
	 */
	public interface IHandler extends IEventDispatcher, IDisposable
	{
		function execute(executionEvent:ExecutionEvent):Object;
		
		function get enabled():Boolean;
		
		function set enabled(value:Boolean):void;
		
		function get handled():Boolean;
		
		function set handled(value:Boolean):void;
	}
}