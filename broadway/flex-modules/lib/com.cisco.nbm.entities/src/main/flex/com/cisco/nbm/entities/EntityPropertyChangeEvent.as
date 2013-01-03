package com.cisco.nbm.entities
{
	import flash.events.Event;

	public class EntityPropertyChangeEvent extends Event
	{
		public static const ENTITY_PROPERTY_CHANGE:String = "entityPropertyChange";
		
		public var entity:Entity;
		
		public var property:EntityProperty;
		
		public var value:Object;
		
		public function EntityPropertyChangeEvent(entity:Entity, property:EntityProperty, value:Object)
		{
			super(ENTITY_PROPERTY_CHANGE);
			this.entity = entity;
			this.property = property;
			
			this.value = value;
		}
		
	}
}