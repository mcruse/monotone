package com.cisco.nbm.entities
{
	import flash.events.Event;

	public class EntityEvent extends Event
	{
		public static const PROPERTIES_LOADED:String = "propertiesLoaded";
		
		public static const DISPLAY_LOADED:String = "displayLoaded";
		
		public static const CHILDREN_LOADED:String = "childrenLoaded";
		
		public function EntityEvent(type:String)
		{
			super(type);
		}
		
	}
}