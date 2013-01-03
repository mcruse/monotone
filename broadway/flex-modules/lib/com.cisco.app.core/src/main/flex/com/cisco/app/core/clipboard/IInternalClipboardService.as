///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.clipboard
{
	import flash.events.IEventDispatcher;
	
	/**
	 * Interface for interfacing with the internal clipboard and 
	 * the system clipboard.
	 */
	public interface IInternalClipboardService extends IEventDispatcher
	{
		function clear():void;
		
		function getData():Object;
		
		function setData(data:Object):void;
	}
}