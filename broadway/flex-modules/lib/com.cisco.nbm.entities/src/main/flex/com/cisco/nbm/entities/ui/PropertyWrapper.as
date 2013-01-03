package com.cisco.nbm.entities.ui
{
	import com.cisco.nbm.entities.Entity;
	import com.cisco.nbm.entities.EntityProperty;
	
	import flash.events.EventDispatcher;
	
	public class PropertyWrapper extends EventDispatcher
	{
		public var property:EntityProperty;
		
		[Bindable]
		public var selected:Boolean = false;
		
		[Bindable]
		public var enabled:Boolean = true;
		
		private var _label:String;
		
		public var entity:Entity;
		
		public var entityName:String;
		
		public var propertyName:String;
		
		public var type:String;
		
		public var path:String;
		
		public function PropertyWrapper(entity:Entity, property:EntityProperty)
		{
			this.entity = entity;
			this.property = property;
			propertyName = property.name;	
			entityName = entity.label;
			this.type = property.type;
			
			path = entity.path + "/properties/" + property.name;
		}

		public function get label():String
		{
			if (property.label != null)
			{
				return property.label + " (" + property.name + ")";
			} 
			
			return property.name;
		}
		
		override public function toString():String
		{
			return "PropertyWrapper(entity="+entityName+", property="+property.label+")";
		}
	}
}