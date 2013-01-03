package com.cisco.nbm.scheduler
{
	import mx.collections.ArrayCollection;
	
	public class ScheduleProperty
	{
		/*
		  [{"property":"/path/to/entity/prop",
    #                  "type":"property_type",
    #                  "valuemap":{"eventname":"eventvalue"}}]
    */
    	public var property:String;
    	
    	public var type:String;
    	
    	/**
    	 * A mapping between the UUID of an eventMeta to a custom value (usually string)
    	 * 
    	 * { 'aaaa-bbbb-ccc-ddd' : "ON", 'eeee-ffff-gggg-hhhh' : 'OFF' }
    	 * 
    	 */
    	public var valuemap:Object = {};
    	
    	/**
    	 * The raw value map returned by the server.
    	 * It is usually just used during initialization and the values
    	 * should be ignored afterwards.  
    	 */
    	public var rawValueMap:Object = {};
    	
    	public var entity:String;
    	
		public function ScheduleProperty()
		{
			
		}
		
		public static function fromEntityPropTuple(entityCanonicalPath:String,
			propertyName:String, type:String):ScheduleProperty
		{
			var schedProp:ScheduleProperty = new ScheduleProperty();
			schedProp.entity = entityCanonicalPath;
			schedProp.property = propertyName;
			schedProp.type = type;
			
			return schedProp;
		}
		
		public function fromDictionary(dict:Object):void
		{
			var deviceManagerRoot:String = "";
			
			property = dict['name'];
			// TODO We're taking off the Device Manager subpath here
			// though we need to identify if this is actually required.
			///Building A/Floor 1/vav1-15/properties/occ
			///aliases/Device Manager/Building A/Floor 1/vav1-15/properties/occ
			//entityPath = 
			
			entity = dict['entity'];
			
			type = dict['type'];
			//valuemap = //dict['valuemap'];
			rawValueMap = dict['valuemap'];
		}
		
		/**
		 * This needs the meta data information to remap the event meta
		 * to the valuemap.
		 * 
		 * It'd be ideal to move it away from here.  
		 */
		public function toDictionary(eventMeta:ArrayCollection):Object
		{
			// NOTE Property path is set to full device manager path 
			// because the framework currently throws an exception otherwise.
			// Convert valuemap to rawValueMap, need external props for that =(
			var newRawMap:Object = {};
			
			for (var uuid:String in valuemap) {
				for each (var meta:EventMetaData in eventMeta) {
					if (meta.uuid == uuid) {
						newRawMap[meta.value] = valuemap[uuid];
						break;
					}
				}
			}
			
			return { 'entity' : entity,
					'type' : type, 
					'name' : property, 
					'valuemap' : newRawMap }; 
		} 
		
		public function isEqual(otherProperty:ScheduleProperty):Boolean
		{
			if (otherProperty == null)
			{
				return false;
			}
			
			return otherProperty.entity == entity &&
				otherProperty.type == type &&
				otherProperty.property == property; 
		}
	}
}