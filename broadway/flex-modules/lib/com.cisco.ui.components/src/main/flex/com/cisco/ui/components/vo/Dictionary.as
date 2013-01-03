package com.cisco.ui.components.vo
{
	import com.cisco.ui.components.event.DictionaryEvent;
	
	import flash.events.Event;
	import flash.events.EventDispatcher;
	import flash.events.IEventDispatcher;
	import flash.utils.flash_proxy;
	
	import mx.events.CollectionEvent;
	import mx.events.CollectionEventKind;
	import mx.utils.ObjectProxy;
	use namespace flash_proxy;


	public dynamic class Dictionary extends ObjectProxy implements IEventDispatcher
	{
		private var _maintainArray:Boolean;
	    private var eventDispatcher:EventDispatcher;
	    protected var _length:int = 0;

		
		public function Dictionary() {
			super();
			eventDispatcher = new EventDispatcher(this);
			setMaintainArray(false);
		}
		
		protected function setMaintainArray(value:Boolean):void {
			_maintainArray = value;
		}
		
		protected function get maintainArray():Boolean {
			return _maintainArray;
		}
		
		public function add(value:IComparator):void {
			if ( value == null || value.uniqueIdentifier() == null )	return;
			if ( dictionary.hasOwnProperty(getKey(value.uniqueIdentifier())) )	return;
			setKeyValue(value.uniqueIdentifier(),value);
		}
		
		public function remove(keyOrValue:Object):void {
			var actualObject:IComparator;
			var key:String;
			if ( keyOrValue is IComparator && (keyOrValue as IComparator).uniqueIdentifier() != null ) {
				key = (keyOrValue as IComparator).uniqueIdentifier();
			} else if ( keyOrValue is String) {
				key = keyOrValue as String;
			}

			if ( key != null ) {
				if ( !dictionary.hasOwnProperty(getKey(key)) )	return;
				if ( maintainArray )
					actualObject = getValue(key) as IComparator;
				removeItem(key,actualObject);
			}
		}
		
		private function removeItem(key:String,value:Object=null):void {
			delete dictionary[getKey(key)];
			_length--;
			if ( maintainArray ) {
				dispatchEvent(new DictionaryEvent(DictionaryEvent.REMOVE,key,value));
			} else {
				dispatchEvent(new CollectionEvent(CollectionEvent.COLLECTION_CHANGE,false,false,CollectionEventKind.RESET));
			}
		}
		
		private function setKeyValue(key:String,value:Object):void {
			dictionary[getKey(key)] = value;
			_length++;
			if ( maintainArray )
				dispatchEvent(new DictionaryEvent(DictionaryEvent.ADD,key,value));
			else {
				dispatchEvent(new CollectionEvent(CollectionEvent.COLLECTION_CHANGE,false,false,CollectionEventKind.RESET));
			}
		}
		
		protected function getKey(key:String):String {
			return key;
		}
		
		public function exists(item:IComparator):Boolean {
			if ( item == null || item.uniqueIdentifier() == null )	return false;
			return existsWithUniqueID(item.uniqueIdentifier());
		}
		
		public function existsWithUniqueID(key:String):Boolean {
			return find(key) != null;
		}
		
		public function replace(value:IComparator):void {
			//Start- Duplicate frameworks display when saving framework
			if ( value == null || value.uniqueIdentifier() == null )	return;
			remove(value);
			//End- Duplicate frameworks display when saving framework
			setKeyValue(value.uniqueIdentifier(),value);
		}
		
		public function getValue(key:String):Object {
//			if ( dictionary.hasOwnProperty(getKey(key)))
				return dictionary[getKey(key)];
			return null;
		}
		
		public function find(key:String):IComparator {
			return getValue(key) as IComparator;
		}
		
		
 		public function get length():int {
 			return _length;
		}
		
		protected function get dictionary():Object {
			return this;
		}
		
		public function get isEmpty():Boolean {
			for ( var key:String in dictionary ) {
				return false;
			}
			return true;
		}
		
		public function hasKey(key:String):Boolean {
			return ( getValue(key) != null);
		}
		
		public function toArray():Array {
			var array:Array = new Array();
			for ( var key:String in dictionary ) {
				array.push(dictionary[key]);
			}
			return array;
		}
		
		

		//--------------------------------------------------------------------------
		//
		// EventDispatcher methods
		//
		//--------------------------------------------------------------------------

	    /**
	     *  @inheritDoc
	     */
	    override public function addEventListener(type:String,
	                                     listener:Function,
	                                     useCapture:Boolean = false,
	                                     priority:int = 0,
	                                     useWeakReference:Boolean = false):void
	    {
	        eventDispatcher.addEventListener(type, listener, useCapture,
	                                         priority, useWeakReference);
	    }
	
	    /**
	     *  @inheritDoc
	     */
	    override public function removeEventListener(type:String,
	                                        listener:Function,
	                                        useCapture:Boolean = false):void
	    {
	        eventDispatcher.removeEventListener(type, listener, useCapture);
	    }
	
	    /**
	     *  @inheritDoc
	     */
	    override public function dispatchEvent(event:Event):Boolean
	    {
	        return eventDispatcher.dispatchEvent(event);
	    }
	
	    /**
	     *  @inheritDoc
	     */
	    override public function hasEventListener(type:String):Boolean
	    {
	        return eventDispatcher.hasEventListener(type);
	    }
	
	    /**
	     *  @inheritDoc
	     */
	    override public function willTrigger(type:String):Boolean
	    {
	        return eventDispatcher.willTrigger(type);
	    }
	    
		//--------------------------------------------------------------------------
		//
		// Proxy methods
		//
		//--------------------------------------------------------------------------
		
/* 		override flash_proxy function getProperty(name:*):*
		{
		    return dictionary[name];
		}
		
		override flash_proxy function setProperty(name:*, value:*):void
		{
			if ( name is QName ) {
				name = name.localName;
			}
			switch ( name ) {
				case "sort" :
			}
		    dictionary[name] = value;
		}
 */		
 
 		override flash_proxy function hasProperty(name:*):Boolean
		{
			return dictionary[name] != null;
		}

	    

	}
}