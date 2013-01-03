package com.cisco.nbm.entities.ui
{
	import com.cisco.nbm.entities.Entity;
	import com.cisco.nbm.entities.EntityEvent;
	import com.cisco.nbm.entities.EntityProperty;
	import com.cisco.nbm.entities.EntityPropertyType;
	
	import mx.collections.ArrayCollection;
	import mx.collections.Sort;
	import mx.collections.SortField;
	import mx.events.CollectionEvent;
	import mx.events.PropertyChangeEvent;

	public class PropertyCollectionWrapper extends ArrayCollection
	{
		private var _wrappers:ArrayCollection = new ArrayCollection();
		
		private var managedEntities:ArrayCollection = new ArrayCollection();		
		
		private var filterEntityName:String = "";
		
		private var filterPropertyName:String = "";
		
		private var _selection:ArrayCollection = new ArrayCollection();
		
		public function PropertyCollectionWrapper()
		{
			var sortField:SortField = new SortField("label");
			this.sort = new Sort();
			this.sort.fields = [sortField];
			this.refresh();
		}
				
		public function get selection():ArrayCollection
		{
			return _selection;
		}
		
		public function updateSelection(selected:Array):void
		{
			if (selected != null && selected.length > 0)
			{
				for each (var item:PropertyWrapper in this)
				{
					for each (var sel:EntityPropertySelectionEntry in selected)
					{
						if (sel.entityCanonicalPath == item.entity.canonicalPath &&
							sel.propertyName == item.propertyName &&
							sel.type == item.type)
							{
								item.selected = true;
								
								_selection.addItem(item);
								
								break;
							}
					}
				}
			}
			else
			{
				for each (var item:PropertyWrapper in this)
				{
					item.selected = false;
					
					var idx:int = _selection.getItemIndex(item);
					if (idx != -1)
					{
						_selection.removeItemAt(idx);
					} 
				}
			}
		}
		
		public function setFilter(entityName:String, propertyName:String):void
		{
			if (entityName.length == 0 && propertyName.length == 0)
			{
				if (filterFunction != null)
				{
					filterFunction = null;
					refresh();
				}
			}
			else
			{
				if (filterEntityName != entityName || filterPropertyName != propertyName)
				{
					filterEntityName = entityName;
					filterPropertyName = propertyName;
					filterFunction = collectionFilterFunction;
					refresh();
				}
				
			}
		}
		
		private function collectionFilterFunction(item:PropertyWrapper):Boolean
		{
			// if both are set, do an and
			if (filterEntityName.length > 0 && filterPropertyName.length > 0)
			{
				if (item.entityName.indexOf(filterEntityName) != -1 &&
					item.propertyName.indexOf(filterPropertyName) != -1)
					{
						return true;
					}
					return false;
			}
				
			
			if (filterEntityName.length > 0 && item.entityName.indexOf(filterEntityName) != -1)
			{
				return true;
			}
			
			if (filterPropertyName.length > 0 && item.propertyName.indexOf(filterPropertyName) != -1)
			{
				return true;
			}
			
			return false;
		}
		
		public function update(entity:Entity):void
		{
			removeAll();
			
				
				if (!entity.propertiesLoaded)
				{
					entity.addEventListener(EntityEvent.PROPERTIES_LOADED, handleEntityPropertiesLoaded);
					entity.loadProperties();
				}
				else
				{
					addEntityProperties(entity);
				}
				
				managedEntities.addItem(entity);
		}
		
		private function handleEntityPropertiesLoaded(event:EntityEvent):void
		{
			var entity:Entity = event.target as Entity;
			
			entity.removeEventListener(EntityEvent.PROPERTIES_LOADED, handleEntityPropertiesLoaded);
			addEntityProperties(entity);
		}
		
		private function addEntityProperties(entity:Entity):void
		{
			var props:ArrayCollection = entity.properties;
			
			for each (var prop:EntityProperty in props)
			{
				if (prop.isOutput() || prop.type == EntityPropertyType.SCHEDULE)
				{
					var wrapper:PropertyWrapper = new PropertyWrapper(entity, prop);
					//_wrappers.addItem(wrapper);
					wrapper.addEventListener(PropertyChangeEvent.PROPERTY_CHANGE, handlePropertyWrapperChange);
					this.addItem(wrapper);
				}
			}
			
			//updateSelection(_selection); // ????
			// Do we have to update selection?
			
		//	var event:CollectionEvent = new CollectionEvent(CollectionEvent.COLLECTION_CHANGE);
		//	event.kind = CollectionEventKind.UPDATE;
		//	dispatchEvent(event);
		}
		
		private function handlePropertyWrapperChange(event:PropertyChangeEvent):void
		{
			var wrapper:PropertyWrapper = event.target as PropertyWrapper;
			
			if (wrapper.selected)
			{
				var idx:int = _selection.getItemIndex(wrapper);
				if (idx == -1)
				{
					_selection.addItem(wrapper);
				}
			}
			else
			{
				var idx:int = _selection.getItemIndex(wrapper);
				
				if (idx != -1)
				{
					_selection.removeItemAt(idx);
				}
			}
			
		}
		
		private function cleanManagedEntities():void
		{
			
			
			for each (var entity:Entity in managedEntities)
			{
				entity.removeEventListener(EntityEvent.PROPERTIES_LOADED, handleEntityPropertiesLoaded);
			}
			
			managedEntities.removeAll();
		}
		
		private function handleCollectionChange(event:CollectionEvent):void
		{
			
		}
		
		private function removeWrapperListeners():void
		{
			for each (var wrapper:PropertyWrapper in this)
			{
				wrapper.removeEventListener(PropertyChangeEvent.PROPERTY_CHANGE, handlePropertyWrapperChange);
			}
		}
		
		public function destroy():void
		{
			_selection.removeAll();
			cleanManagedEntities();
			removeWrapperListeners();
			
		}
	}
}