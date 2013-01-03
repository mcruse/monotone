///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.operations
{
	public class NullProgressMonitor implements IProgressMonitor
	{
		public function NullProgressMonitor()
		{
		}

		public function beginTask(name:String, totalWork:uint):void
		{
			trace("begin task: " + name + ", " + totalWork);
		}
		
		public function work(amount:uint):void
		{
			trace("work: " + amount);
		}
		
		public function done():void
		{
			trace("done");
		}
		
		public function get canceled():Boolean
		{
			return false;
		}
		
		public function set canceled(value:Boolean):void
		{
		}
		
		public function get taskName():String
		{
			return "";
		}
		
		public function set taskName(value:String):void
		{
			trace("set task name: " +value);
		}
		
	}
}