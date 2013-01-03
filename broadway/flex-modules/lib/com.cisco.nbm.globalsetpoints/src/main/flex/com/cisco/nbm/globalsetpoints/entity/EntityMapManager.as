package com.cisco.nbm.globalsetpoints.entity
{
	import flash.events.Event;
	import flash.events.EventDispatcher;
	
	[Event(name="onPollResult", type="flash.events.Event")]
	
	import mx.collections.ArrayCollection;
	
	public class EntityMapManager extends EventDispatcher
	{
		import mx.controls.Alert;
		import mx.utils.ObjectUtil;
		import com.cisco.nbm.globalsetpoints.SetpointDatatype;
		import com.cisco.nbm.xmlrpc.v2.MediatorNode;
		import com.cisco.nbm.xmlrpc.v2.MediatorNodeCall;
		import com.cisco.nbm.globalsetpoints.entity.EntitySubscriber;

		public  var removedEntities:Object;
		public  var backupEntities:Object;
		
		[Bindable]
		public var configData:ArrayCollection;
		
		private var _numOfValueMismatchEntries:Number = 0;
		private var entityObject:Object;
		private var entitySubscriber:EntitySubscriber;
		
		public function EntityMapManager(_entityObject:Object)
		{
			parseInit(_entityObject);
		}
		
		public function loadSubscription(_subscriptionNode:MediatorNode):void{
			entitySubscriber = new EntitySubscriber(_subscriptionNode);
			entitySubscriber.addEventListener("onPollResult", onPollResult);
			entitySubscriber.addEventListener(EntitySubscriberEvent.READY, 
				handleEntitySubscriberReady);
			updateSubscription();
		}
		
		public function stop():void {
			if (entitySubscriber.isRunning) {
				entitySubscriber.stop();
				entitySubscriber.removeEventListener("onPollResult", onPollResult);
			}
		}
		
		private function handleEntitySubscriberReady(event:EntitySubscriberEvent):void {
			entitySubscriber.start();
		}
		
		public function updateSubscription():void{
			var subcriptionEntities:ArrayCollection = new ArrayCollection();
			for(var i:String in entityObject){
				for(var k:int=0; k<entityObject[i].length; k++){
					var obj:Object = new Object();
					obj.entity_path = entityObject[i][k].entity_path;
					obj.type = entityObject[i][k].property[0];
					obj.property = entityObject[i][k].property[1];
					subcriptionEntities.addItem(obj);
				}
			}

			
			// Create Subscription for created items
			
			if (entitySubscriber.isRunning) {
				entitySubscriber.stop();
			}
			entitySubscriber.create(subcriptionEntities);
			//entitySubscriber.start();
		}
		
		public function refreshSubscription():void
		{
			entitySubscriber.refresh();
		}
		
		private function onPollResult(event:Event):void{
			// Dispatch poll complete event
			var onChangeEvent:Event = new Event( "onPollResult" );
			dispatchEvent( onChangeEvent );
		}
		
		private function parseInit(_entityObject:Object):void{
			// Modifying the object so that setpoint objects are converted into Array
			// Dictionary results in object :: need to fix in back end
			var modEntityObject:Object = new Object();
			for (var i:String in _entityObject){
				modEntityObject[i] = new Array();
				for (var k:String in _entityObject[i]){
					modEntityObject[i].push(_entityObject[i][k]);
				}
			}
			// End of datatype conversion
			entityObject = modEntityObject;
			backupEntities = ObjectUtil.copy(_entityObject as Object) as Object;
			removedEntities = new Object();
		}
		
		public function get entityMap():Object{
			return entityObject;
		}
		
		public function set entityMap(_entityObject:Object):void{
			entityObject = _entityObject;
		}
		
		public function reset():void{
			entityMap = backupEntities;
		}
		
		public function isEntityPresent(_setpointId:String):Boolean{
			if(entityObject.hasOwnProperty(_setpointId)){
				if(entityObject[_setpointId].length <= 0){
					return false;
				}
			} else {
				return false;
			}
			return true;
		}
		
		public function getEntityMapForSetpoint(_setpointId:String):ArrayCollection{
			var mapArr:ArrayCollection = new ArrayCollection();
			
			if(entityObject[_setpointId] != null){
				//for (var i:String in entityObject[_setpointId]){
				for(var i:int=0; i<entityObject[_setpointId].length; i++){
					var obj:Object = new Object();
					obj.entity = entityObject[_setpointId][i].entity_path;
					
					obj.type = entityObject[_setpointId][i].property[0];
					obj.property = entityObject[_setpointId][i].property[1];
					
					/* var propStr:String = entityObject[_setpointId][i].property; // TODO: Currently returend as string from XML RPC
					var prop_arr:Array;
					prop_arr = propStr.split("");
					prop_arr.shift();
					prop_arr.shift();
					prop_arr.pop();
					prop_arr.pop();
					propStr = prop_arr.join("");
					prop_arr = propStr.split("', '");
					obj.property = prop_arr[1];
					obj.type = prop_arr[0]; */
					mapArr.addItem(obj);
				}
			}
			
			return mapArr;
		}
		
		public function getEntityMapFor(GSPItem:String):ArrayCollection {
			
			_numOfValueMismatchEntries = 0;
			
			if(GSPItem == null) return new ArrayCollection();
			
			var retArr:ArrayCollection = new ArrayCollection(entityObject[GSPItem]);

			var mapArr:ArrayCollection = new ArrayCollection();
			var obj:Object;
			for(var k:int=0; k<retArr.length; k++){
				obj = new Object();
				
				var setpointValue:String = getValueForSetpoint(GSPItem);
				var currentValue:String = entitySubscriber.getValueFor({'entity_path':retArr[k].entity_path,
					'type':retArr[k].property[0],
					'property':retArr[k].property[1]});
				// In case of ENUM datatype show the corresponding label
				if(isEnumDataType(GSPItem)){
					currentValue  = getEnumLabelForValue(GSPItem, currentValue);
					setpointValue = getEnumLabelForValue(GSPItem, setpointValue);
				}
				
				obj = { 'property':retArr[k].property[1],
						'type':retArr[k].property[0],
						'value':currentValue,
						'setpoint_value':setpointValue
				} 
				if(currentValue != setpointValue){
					_numOfValueMismatchEntries++;
				}
				
				mapArr.addItem({'entity':retArr[k].entity_path, 'property':obj});
			}
			return mapArr;
		}
		
		public function getEntityMapForAll():ArrayCollection {
			_numOfValueMismatchEntries = 0;
			var mapArr:ArrayCollection = new ArrayCollection();
			var allObj:Object = new Object();
			for(var i in entityObject){
				for(var k:int=0; k<entityObject[i].length; k++){
					if(!allObj.hasOwnProperty( entityObject[i][k].entity_path )){
						allObj[ entityObject[i][k].entity_path ] = new Object();
					}
					
					if(!allObj[ entityObject[i][k].entity_path ].hasOwnProperty( i )){
						allObj[ entityObject[i][k].entity_path ][i] = new Array();
					}
					var obj:Object = new Object();
					obj.type = entityObject[i][k].property[0];
					obj.property = entityObject[i][k].property[1];
					allObj[ entityObject[i][k].entity_path ][i].push(obj);
				}
			}
			// Expand
			for(var i in allObj){
				var cmax:Number = 0;
				
				for(var m:String in allObj[i]){
					var propArray:Array = allObj[i][m];
					if(propArray.length > cmax) cmax = propArray.length;
				}
				//*********************************
				
				for(k=0; k<cmax; k++){					
					var obj:Object = new Object();
					obj.entity = i;
					for(m in allObj[i]){
						if(allObj[i][m][k] != undefined){
							var setpointValue:String = getValueForSetpoint(m);
							var currentValue:String = entitySubscriber.getValueFor({'entity_path':i,
																'type':allObj[i][m][k].type,
																'property':allObj[i][m][k].property});
							// In case of ENUM datatype show the corresponding label
							if(isEnumDataType(m)){
								currentValue  = getEnumLabelForValue(m, currentValue);
								setpointValue = getEnumLabelForValue(m, setpointValue);
							}
							
							//obj[m] = allObj[i][m][k].property+" (" + currentValue + ")";
							 obj[m] = { 'property':allObj[i][m][k].property,
										'type':allObj[i][m][k].type,
										'value':currentValue,
										'setpoint_value':setpointValue
									 } 
							if(currentValue != setpointValue){
								_numOfValueMismatchEntries++;
							}
						}
						
					}
					mapArr.addItem(obj);
				}
			}
			return mapArr;
		}
		
		public function get numOfValueMismatchEntries():Number{
			return _numOfValueMismatchEntries;
		}
		
		public function getAllPropertiesForSetpoint(_setpointId:String):ArrayCollection{
			var mapArr:ArrayCollection = new ArrayCollection();
			if(entityObject[_setpointId] != null){
				for(var k:int=0; k<entityObject[_setpointId].length; k++){
					var obj:Object = new Object();
					obj.entity = entityObject[_setpointId][k].entity_path;
					obj.type = entityObject[_setpointId][k].property[0];
					obj.property = entityObject[_setpointId][k].property[1];
					mapArr.addItem(obj);
				}
			}
			return mapArr;
		}
		
		public function getAllPropertiesForSetpointExcept(_setpointId:String):ArrayCollection{
			var mapArr:ArrayCollection = new ArrayCollection();
			for(var i in entityObject){
				if(i != _setpointId){
					for(var k:int=0; k<entityObject[i].length; k++){
						var obj:Object = new Object();
						obj.entity = entityObject[i][k].entity_path;
						obj.type = entityObject[i][k].property[0];
						obj.property = entityObject[i][k].property[1];
						mapArr.addItem(obj);
					}
				}
			}
			return mapArr;
		}
		
		public function getAllProperties():ArrayCollection{
			var mapArr:ArrayCollection = new ArrayCollection();
			for(var i in entityObject){
				for(var k:int=0; k<entityObject[i].length; k++){
					var obj:Object = new Object();
					obj.entity = entityObject[i][k].entity_path;
					obj.type = entityObject[i][k].property[0];
					obj.property = entityObject[i][k].property[1];
					mapArr.addItem(obj);
				}
			}
			return mapArr;
		}
		
		public function removeSetpointMap(_setpointId:String):void{
			if(entityObject[_setpointId] != null){
				entityObject[_setpointId] = undefined;
				delete entityObject[_setpointId];
			}
		}
		
		public function get setpoints():Array {
			var spList:Array= new Array();
			for(var i:String in entityObject){
				spList.push(i);
			}
			return spList;
		}
		
		public function updateEntityMap(_setpointId:String, newmap:Array):void{
			entityObject[_setpointId] = new Array();
			for(var i:int=0; i<newmap.length; i++){
				entityObject[_setpointId][i] = new Object();
				entityObject[_setpointId][i].setpoint_id = _setpointId;
				entityObject[_setpointId][i].entity_path =  newmap[i].entity;
				entityObject[_setpointId][i].property    =  [newmap[i].type,newmap[i].property];
				entityObject[_setpointId][i].config      =  new Object();
			}
			updateSubscription();
		}
		
		/**
		 * Checks if the provided setpoint is an ENUM datatype
		 * @param _setpointId
		 * @return 
		 * 
		 */		
		private function isEnumDataType(_setpointId:String):Boolean{
			if(configData == null) return false;
			for(var i:int=0; i<configData.length; i++){
				if(configData.getItemAt(i).setpoint_id == _setpointId){
					if( configData.getItemAt(i).data_type.hasOwnProperty(SetpointDatatype.ENUMERATED) ){
						return true;
					}
				}
			}
			return false;
		}
		
		/**
		 * Provides the enum label for a given value
		 * Used to show defined label for an enum datatype 
		 * @param _setpointId
		 * @param _value
		 * @return 
		 * 
		 */		
		private function getEnumLabelForValue(_setpointId:String, _value:String):String{
			if(configData == null) return _value;
			var enumObj:Object;
			for(var i:int=0; i<configData.length; i++){
				if(configData.getItemAt(i).setpoint_id == _setpointId){
					if( configData.getItemAt(i).data_type.hasOwnProperty(SetpointDatatype.ENUMERATED) ){
						enumObj = configData.getItemAt(i).data_type[SetpointDatatype.ENUMERATED];
					}
				}
			}
			if(enumObj != null){
				for(var key:String in enumObj){
					if(enumObj[key] == _value){
						return key;
					}
				}
			}
			return _value;
		}
		
		private function getValueForSetpoint(_setpointId:String):String{
			if(configData == null) return "";
			for(var i:int=0; i<configData.length; i++){
				if(configData.getItemAt(i).setpoint_id == _setpointId){
					return configData.getItemAt(i).value;
				}
			}
			return "";
		}
		
		// Remove Object
		public function removeObject(_setpointId:String, objectToRemove:Object):void{
			if(removedEntities[_setpointId] == null){
				removedEntities[_setpointId] = new Array();
			}
			
			for(var i:int=0; i<entityObject[_setpointId].length; i++){
				if(!objectToRemove.hasOwnProperty(_setpointId)){
					//break;
				}
				if(entityObject[_setpointId][i].entity_path == objectToRemove.entity &&
				entityObject[_setpointId][i].property[0] == objectToRemove.property.type &&
					entityObject[_setpointId][i].property[1] == objectToRemove.property.property){
						removedEntities[_setpointId].push(entityObject[_setpointId][i]);
						entityObject[_setpointId].splice(i,1);
					}
			}
		}
	}
}