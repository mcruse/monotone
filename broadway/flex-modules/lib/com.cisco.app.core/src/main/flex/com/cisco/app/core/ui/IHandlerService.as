///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.ui
{
	import flash.events.IEventDispatcher;

	/**
	 * 
	 * 
	 * @author Robert Cadnea
	 */
	public interface IHandlerService extends IEventDispatcher
	{
		function activateHandler(commandId:String, handler:IHandler):void;
		
		function executeCommand(commandId:String, parameters:Object=null, event:Object=null):Object;
	}
}