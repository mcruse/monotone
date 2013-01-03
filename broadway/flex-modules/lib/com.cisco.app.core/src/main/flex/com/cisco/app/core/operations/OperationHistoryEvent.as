///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.operations
{
	import flash.events.Event;

	public class OperationHistoryEvent extends Event
	{
		public static const BEGIN_UNDOING:String = "beginUndoing";
		
		public static const BEGIN_ASYNC:String = "beginAsync";
		
		public static const END_ASYNC:String = "endAsync";
		
		public function OperationHistoryEvent(type:String, bubbles:Boolean=false, cancelable:Boolean=false)
		{
			super(type, bubbles, cancelable);
		}
		
	}
}