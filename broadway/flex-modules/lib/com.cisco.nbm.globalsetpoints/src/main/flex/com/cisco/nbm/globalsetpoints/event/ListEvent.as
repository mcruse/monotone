package com.cisco.nbm.globalsetpoints.event
{
	import flash.events.Event;
	
	public class ListEvent extends Event
	{
		public static const NEW_SETPOINT:String   = "newsetpoint";
		public static const VIEW_SETPOINT:String  = "viewsetpoint";
		public static const CLOSE_SETPOINT:String = "closesetpoint";
		
		// Propoerties
		public var setpointList:Array;
		public var selectedSetpoint:Object;
		public var newName:String;
		
		public function ListEvent(eventString:String)
		{
			super(eventString);
		}

	}
}

 