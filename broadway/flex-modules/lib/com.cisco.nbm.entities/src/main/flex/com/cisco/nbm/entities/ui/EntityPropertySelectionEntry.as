package com.cisco.nbm.entities.ui
{
	import com.cisco.nbm.entities.Entity;
	
	public class EntityPropertySelectionEntry
	{
		/*
		arr.push( { 'entityName' : prop.entity, 
						'propertyName' : prop.property,
						'type' : prop.type,
						'path' : prop.path  } );
		*/
		
		public var entityCanonicalPath:String;
		
		public var propertyName:String;
		
		public var type:String;
		
		public function EntityPropertySelectionEntry(entityCanonicalPath:String,
			propertyName:String, type:String)
		{
			this.entityCanonicalPath = entityCanonicalPath;
			this.propertyName = propertyName;
			this.type = type;
			
		}
		
		public function wrapperEquals(wrapper:PropertyWrapper):Boolean
		{
			return entityCanonicalPath == wrapper.entity.canonicalPath
				&& propertyName == wrapper.propertyName 
				&& type == wrapper.type; 
		}

	}
}