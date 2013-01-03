///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.operations
{
	public interface IProgressMonitor
	{
		function beginTask(name:String, totalWork:uint):void;
		
		function work(amount:uint):void;
		
		function done():void;
		
		function get canceled():Boolean;
		
		function set canceled(value:Boolean):void;
		
		function get taskName():String;
		
		function set taskName(value:String):void;
	}
}