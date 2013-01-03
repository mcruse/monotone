package com.cisco.nbm.scheduler.ui.schedules
{
	import com.cisco.nbm.scheduler.ScheduleProperty;
	
	import mx.collections.ArrayCollection;
	
	public class SchedulePropertyModelWrapper extends ArrayCollection
	{
		public var entityName:String;
		
		public var propertyName:String;
		
		public var _properties:ArrayCollection  /* of ScheduleProperty */= new ArrayCollection();
		
		public function SchedulePropertyModelWrapper(entityName:String)
		{
			this.entityName = entityName;
		}

		override public function get length():int
		{
			return _properties.length;
		}
		
		override public function getItemAt(index:int, prefetch:int=0):Object
		{
			return _properties.getItemAt(index, prefetch);
		}
		
		public function addProperty(property:ScheduleProperty):void
		{
			_properties.addItem(property);
		}

	}
}