package com.cisco.nbm.globalsetpoints.entity
{
	import flash.events.Event;
	import flash.events.EventDispatcher;
	
	import mx.controls.Alert;
	[Event(name="onChangeResult", type="flash.events.Event")]
	public class DiscoveryManager extends EventDispatcher
	{
		import mx.collections.ArrayCollection;
		import mx.controls.Alert;
		
		import com.cisco.nbm.entities.ui.PropertyCollectionWrapper;
		import mx.events.CollectionEvent;
		import com.cisco.nbm.entities.EntityManager;
		import com.cisco.nbm.entities.Entity;
		import com.cisco.nbm.entities.EntityEvent;
		
		private var _typeResults:ArrayCollection;
		private var _nameResults:ArrayCollection;
		private var temp_nameResults:Array;
		private var entity:Entity;
		
		private var _propertyWrapper:PropertyCollectionWrapper;
		private var pollCount:Number;
		
		public  var searchType:String;
		public  var point_type:String;
		public  var entityManager:EntityManager;
		public  var selectedEntities:ArrayCollection;
		public  var disabledEntities:ArrayCollection;
		
		public function DiscoveryManager()
		{
			_propertyWrapper = new PropertyCollectionWrapper();
		}
		
		public function set typeResults(resultObj:Object):void{
			searchType = "type";
			_typeResults = new ArrayCollection();
			for(var i:String in resultObj){
				
				for(var k in resultObj[i]){
					// 'property' and 'type'
					var propArr:Array = resultObj[i][k];
					for(var n:int = 0; n<propArr.length; n++ ){
						var obj:Object = new Object();
						obj.entity = '/aliases' + i.split(" ").join("%20");
						obj.type     = propArr[n][0];
						obj.property = propArr[n][1];
						obj.selected = true;  // Add selected property and make it selected by default
						obj.enabled = true;
						// Checl if already selected
						for(var j:int=0; j<selectedEntities.length; j++){
							if(selectedEntities.getItemAt(j).entity == obj.entity &&
							   selectedEntities.getItemAt(j).property == obj.property &&
							   selectedEntities.getItemAt(j).type == obj.type){
								obj.enabled = false;
							}
						}
						
						// Checl if disabled
						for(var j:int=0; j<disabledEntities.length; j++){
							if(disabledEntities.getItemAt(j).entity == obj.entity &&
							   disabledEntities.getItemAt(j).property == obj.property &&
							   disabledEntities.getItemAt(j).type == obj.type){
							   	obj.selected = false;
								obj.enabled = false;
							}
						}
						_typeResults.addItem(obj);
					}
					
				}
			}
			onChangeResult();
		}
		
		public function set nameResults(resultArr:Array):void{
			_nameResults = new ArrayCollection();
			searchType = "name";
			temp_nameResults = resultArr;
			pollCount = 0;

			if(temp_nameResults.length > 0){
				var newSearchObject:Object;
				for(var i:int = 0; i<temp_nameResults.length; i++){
					newSearchObject = new Object();
					newSearchObject.entity = temp_nameResults[i];
					newSearchObject.property = "Loading....";
					_nameResults.addItem(newSearchObject);
				}
				onChangeResult();
			} else {
				onChangeResult();
			}
		}
		/**
		 * On result is updated after formatting 
		 * Need to wait for properties in case of search by name
		 */		
		private function onChangeResult():void{
			var onChangeEvent:Event = new Event( "onChangeResult" );
			dispatchEvent( onChangeEvent );
		}
		
		[Bindable]
		public function get results():ArrayCollection{
			if(searchType == "type"){
				return _typeResults;
			}
			return _nameResults;
		}
		public function set results(value:ArrayCollection):void{
			_nameResults = value;
		}
		
		private function loadProperties(_entityPath:String):void{
			// Remove 'aliases' path from entity path
			var entityPathArr:Array = _entityPath.split("/");
			entityPathArr.shift();
			entityPathArr.shift();
			var entityPathStr:String = "/"+entityPathArr.join("/");
			
			entity = entityManager.getEntity(entityPathStr);
			_propertyWrapper.update(entity);
			
			if(entity.properties.length > 0){
				parseProperties();
			} else {
				entity.addEventListener(EntityEvent.PROPERTIES_LOADED,onPropertyLoad);
				entity.loadProperties(true);
			};
			
		}
		public function onPropertyLoad(event:EntityEvent):void{
			entity.removeEventListener(EntityEvent.PROPERTIES_LOADED,onPropertyLoad);
			parseProperties();
		}
		
		private var tempObj:Object = {};
		private function parseProperties():void{
			// Remove dupes
			tempObj = {};
			for(var i:int=0; i<_propertyWrapper.length; i++){
				var obj:Object = new Object();
				if (!tempObj.hasOwnProperty(_propertyWrapper.getItemAt(i).propertyName)) {
					tempObj[_propertyWrapper.getItemAt(i).propertyName] = _propertyWrapper.getItemAt(i);
					obj.entity   = _propertyWrapper.getItemAt(i).entity.canonicalPath;
					obj.property = _propertyWrapper.getItemAt(i).propertyName;
					obj.type     = _propertyWrapper.getItemAt(i).type;
					obj.selected = true;
					obj.enabled  = true;
					// Check if already selected
					for(var k:int=0; k<selectedEntities.length; k++){
						if(selectedEntities.getItemAt(k).entity == obj.entity &&
						   selectedEntities.getItemAt(k).property == obj.property &&
						   selectedEntities.getItemAt(k).type == obj.type){
							obj.enabled = false;
						}
					}
					
					// Checl if disabled
					for(var j:int=0; j<disabledEntities.length; j++){
						if(disabledEntities.getItemAt(j).entity == obj.entity &&
						   disabledEntities.getItemAt(j).property == obj.property &&
						   disabledEntities.getItemAt(j).type == obj.type){
						   	obj.selected = false;
							obj.enabled = false;
						}
					}
					_nameResults.addItem(obj);
				}
				
			}
			
			// Get property for next entity
			if(pollCount < temp_nameResults.length - 1){
				pollCount++;
				loadProperties(temp_nameResults[pollCount]);
			} else {
				// Dispatch result complete event
				onChangeResult();
			}
		}
	}
}