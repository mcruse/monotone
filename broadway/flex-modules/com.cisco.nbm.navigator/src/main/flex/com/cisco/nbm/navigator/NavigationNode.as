package com.cisco.nbm.navigator
{
	import flash.events.EventDispatcher;

	public class NavigationNode extends EventDispatcher
	{
		protected var _children:ArrayCollection = new ArrayCollection();
	
		public var label:String;
		
		public var uuid:String;
			
		public function NavigationNode(label:String, uuid:String)
		{
			super();
			
			this.label = label;
			this.uuid = uuid;
		}
		
		public function get uuid():String
		{
			return _uuid;
		}
		
		public function get label():String
		{
			return _label;
		}
		
		[Bindable]
		public function get children():ArrayCollection
		{
			return _children;
		}
		
		public function set children(value:ArrayCollection):void
		{
			throw new Error("Property is read-only");
		}	
	}
}