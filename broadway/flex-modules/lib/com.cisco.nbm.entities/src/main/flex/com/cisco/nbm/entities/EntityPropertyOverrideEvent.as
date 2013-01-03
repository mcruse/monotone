package com.cisco.nbm.entities
{
	import flash.events.Event;
	
	public class EntityPropertyOverrideEvent extends Event
	{
		public static const ON_COMPLETE:String = "overrideComplete";
		public static const ON_ERROR:String = "overrideError";
		
		public var entity:Entity;
		public var error:String;
		
		public function EntityPropertyOverrideEvent(type:String)
		{
			super(type);
		}
		
	}
}