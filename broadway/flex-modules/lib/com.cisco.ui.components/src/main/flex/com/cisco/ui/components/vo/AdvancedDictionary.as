package com.cisco.ui.components.vo
{
	import com.cisco.ui.components.event.DictionaryEvent;
	
	import flash.utils.flash_proxy;
	
	import mx.collections.ArrayCollection;
	import mx.collections.ICollectionView;
	import mx.collections.IViewCursor;
	import mx.collections.Sort;
	import mx.events.CollectionEvent;
	import mx.events.CollectionEventKind;
	use namespace flash_proxy;


	public class AdvancedDictionary extends Dictionary implements ICollectionView
	{
		protected var keys:ArrayCollection;
		protected var values:ArrayCollection;
		protected var isRefreshing:Boolean=false;
		protected var _dictionary:DynamicObject = new DynamicObject();

		public function AdvancedDictionary()
		{
			super();
		}
		
		override protected function setMaintainArray(value:Boolean):void {
			super.setMaintainArray(true);
			keys = new ArrayCollection();
			values = new ArrayCollection();
			addEventListener(DictionaryEvent.ADD,addToArray);
			addEventListener(DictionaryEvent.REMOVE,removeFromArray);
		}
		
		override protected function get dictionary():Object {
			return _dictionary;
		}

		
		protected function addToArray(event:DictionaryEvent):void {
			while (isRefreshing) {
				
			}
			isRefreshing = true;
			
			var anIndex:int = this.keys.getItemIndex(event.key);
			if ( anIndex == -1 ) {
				this.keys.addItem(event.key);
			}
			
			anIndex = this.values.getItemIndex(event.value);
			if ( anIndex == -1 ) {
				this.values.addItem(event.value);
			}
			
			isRefreshing = false;
			dispatchEvent(new CollectionEvent(CollectionEvent.COLLECTION_CHANGE,false,false,CollectionEventKind.ADD,this.values.getItemIndex(event.value),anIndex,[event.value]));
		}
		
		protected function removeFromArray(event:DictionaryEvent):void {
			while (isRefreshing) {
				
			}
			isRefreshing = true;
			var anIndex:int = this.keys.getItemIndex(event.key);
			
			if ( anIndex != -1 )
				this.keys.removeItemAt(this.keys.getItemIndex(event.key));
				
			anIndex = this.values.getItemIndex(event.value);
			if ( anIndex != -1 )
				this.values.removeItemAt(this.values.getItemIndex(event.value));
				
			isRefreshing = false;
			dispatchEvent(new CollectionEvent(CollectionEvent.COLLECTION_CHANGE,false,false,CollectionEventKind.REMOVE,this.values.getItemIndex(event.value),anIndex,[event.value]));
		}
		
		public function dispatchChangeEvent():void {
			dispatchEvent(new CollectionEvent(CollectionEvent.COLLECTION_CHANGE,true,false,CollectionEventKind.REFRESH));
		}

		override public function toArray():Array {
			while(isRefreshing) {
				
			}
			return this.values.toArray();
		}

		
		public function get allKeys(): ArrayCollection {
			if ( maintainArray ) {
				while(isRefreshing) {
					
				}
				return new ArrayCollection(this.keys.toArray());
			}
			return null;
		}
		
		public function get allValues(): ArrayCollection {
			if ( maintainArray ) {
				while(isRefreshing) {
					
				}
				return new ArrayCollection(this.values.toArray());
			}
			return null;
		}

		
		
		override public function get length():int
		{
			return values.length;
		}
		
		public function disableAutoUpdate():void
		{
			values.disableAutoUpdate();
		}
		
		public function createCursor():IViewCursor
		{
			return values.createCursor();
		}
		
		public function get filterFunction():Function
		{
			return values.filterFunction;
		}
		
		public function set filterFunction(value:Function):void
		{
			values.filterFunction = value;
		}
		
		public function contains(item:Object):Boolean
		{
			return values.contains(item);
		}
		
		public function get sort():Sort
		{
			return values.sort;
		}
		
		public function set sort(value:Sort):void
		{
			values.sort = value;
		}
		
		public function itemUpdated(item:Object, property:Object=null, oldValue:Object=null, newValue:Object=null):void
		{
			values.itemUpdated(item,property,oldValue,newValue);
		}
		
		public function refresh():Boolean
		{
			return values.refresh();
		}
		
		public function enableAutoUpdate():void
		{
			values.enableAutoUpdate();
		}
		
		
		//--------------------------------------------------------------------------
		//
		// Proxy methods
		//
		//--------------------------------------------------------------------------
		
		override flash_proxy function nextNameIndex(index:int):int
		{
			return index < values.length ? index + 1 : 0;
		}
		
		override flash_proxy function nextName(index:int):String
		{
			return (index-1).toString();
		}
		
		override flash_proxy function nextValue(index:int):*
		{
		    return values.getItemAt(index - 1);
		}    
		
		override flash_proxy function callProperty(name:*, ... rest):*
		{
		    return null
		}

		
	}
}