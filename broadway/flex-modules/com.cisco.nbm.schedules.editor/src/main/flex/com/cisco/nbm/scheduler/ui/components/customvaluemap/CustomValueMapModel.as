package com.cisco.nbm.scheduler.ui.components.customvaluemap
{
	import com.cisco.nbm.scheduler.EventMetaData;
	import com.cisco.nbm.scheduler.ScheduleProperty;
	
	import flash.utils.Dictionary;
	
	import mx.collections.ArrayCollection;
	import mx.utils.StringUtil;

	public class CustomValueMapModel extends ArrayCollection
	{
		private var _property:ScheduleProperty;
		
		private var _eventMeta:ArrayCollection;
		
		private var created:Boolean = false;
		
		public function CustomValueMapModel(source:Array=null)
		{
			super(source);
		}
		
		public function set property(value:ScheduleProperty):void
		{
			if (value != _property)
			{
				_property = value;
				createContents();
			}
		}
		
		public function set eventMeta(value:ArrayCollection):void
		{
			if (value != _eventMeta)
			{
				_eventMeta = value;
				createContents();
			}
		}
		
		public function toValueMap():Object
		{
			//var result:Object = {};
			var result:Dictionary = new Dictionary();
			
			for each (var entry:CustomValueMapEntry in this)
			{
				var customValue:String = entry.customValue as String;
				
				if (customValue == null)
				{
					continue;
				}
				
				customValue = StringUtil.trim(customValue);
				
				if (customValue.length == 0)
				{
					customValue = null;
				}
				
				// To convert to string
				result[new String(entry.metaUUID)] = customValue;
			}
			
			return result;
		}
		
		private function createContents():void
		{
			if (_property == null || _eventMeta == null)
			{
				return;
			}
			
			if (created)
			{
				return;
			}
			
			created = true;
			
			var valueMap:Object = _property.valuemap;
			
			for each (var _entry:EventMetaData in _eventMeta)
			{
				var newEntry:CustomValueMapEntry = new CustomValueMapEntry();
				newEntry.name = _entry.name;
				newEntry.realValue = _entry.value;
				newEntry.metaUUID = _entry.uuid;
				
				// find custom value in properties valuemap
				//if (valueMap[_entry.name] != null)
				
				//if (valueMap[_entry.value] != null)
				// Now map the UUID to the value
				if (valueMap[_entry.uuid] != null)  {
					//newEntry.customValue = valueMap[_entry.name];
					newEntry.customValue = valueMap[_entry.uuid];
				}
				
				addItem(newEntry);
			}
		}
		
		public function destroy():void
		{
			for each (var entry:CustomValueMapEntry in this)
			{
				var idx:int = getItemIndex(entry);
				
				entry.destroy();
				
				removeItemAt(idx);
			}
		}
		
	}
}