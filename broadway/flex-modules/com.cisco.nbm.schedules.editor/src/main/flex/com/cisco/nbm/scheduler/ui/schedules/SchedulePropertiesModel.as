package com.cisco.nbm.scheduler.ui.schedules
{
	import com.cisco.nbm.entities.EntityManager;
	import com.cisco.nbm.scheduler.ScheduleProperty;
	
	import mx.collections.ArrayCollection;
	import mx.collections.Sort;
	import mx.collections.SortField;
	import mx.events.CollectionEvent;
	import mx.events.CollectionEventKind;
	
	/**
	 * This model represents the list of properties managed by a schedule.
	 * 
	 * The properties includes a list of entities and each entity contains 
	 * a list of properties.  
	 * 
	 * All entities and their properties must be loaded before the editor can 
	 * be used.  This is so that all the properties for each of the entities 
	 * are present and known before the user can edit or before the editor
	 * can render the controls.
	 * 
	 */ 
	public class SchedulePropertiesModel extends ArrayCollection
	{
		public var propertyList:ArrayCollection = new ArrayCollection();
		
		public function SchedulePropertiesModel(entityManager:EntityManager, 
			properties:ArrayCollection /* of ScheduleProperty */)
		{
			var sort:Sort = new Sort();
			var sortField:SortField = new SortField("entity");
			sort.fields = [sortField];
			propertyList.sort = sort;
			propertyList.refresh();
			updatePropertyList(properties);
		}
		
		private function updatePropertyList(props:ArrayCollection):void
		{
			// Sort the property list by property ...
			for each (var prop:ScheduleProperty in props)
			{
				propertyList.addItem(prop); /// TODO Determine better strategy
			}
			
			var event:CollectionEvent = new CollectionEvent(CollectionEvent.COLLECTION_CHANGE);
			event.kind = CollectionEventKind.REFRESH;
			
			dispatchEvent(event);
		}
		
		private function findEntityByName(entityName:String):SchedulePropertyModelWrapper
		{
			for each (var wrapper:SchedulePropertyModelWrapper in propertyList)
			{
				if (wrapper.entityName == entityName)
				{
					return wrapper;
				}
			}
			
			return null;
		}
		
		private function createPropertyWrapper(entityName:String):SchedulePropertyModelWrapper
		{
			var wrapper:SchedulePropertyModelWrapper = new SchedulePropertyModelWrapper(entityName);
			return wrapper;
		}
		
		
		override public function getItemAt(index:int, prefetch:int=0):Object
		{
			return propertyList.getItemAt(index);
		}
		
		override public function get length():int
		{
			return propertyList.length;
		}
	}
}