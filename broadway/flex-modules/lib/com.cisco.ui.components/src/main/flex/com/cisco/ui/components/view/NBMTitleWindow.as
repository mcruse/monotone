package com.cisco.ui.components.view
{
	import com.cisco.ui.components.event.UIDataEvent;
	
	import flash.events.Event;
	import flash.events.KeyboardEvent;
	import flash.ui.Keyboard;
	
	import mx.containers.TitleWindow;
	import mx.events.CloseEvent;
	import mx.managers.PopUpManager;

	[Event(name="windowClose", type="com.cisco.ui.components.events.UIDataEvent")]
	
	public class NBMTitleWindow extends TitleWindow
	{
		public function NBMTitleWindow() {
			super();
			addEventListener(CloseEvent.CLOSE,closeHandler);
		}
		
		override protected function keyDownHandler(event:KeyboardEvent):void {
			switch(event.keyCode) {
				case Keyboard.ESCAPE :
					closeThis();
					return;
			}
			super.keyDownHandler(event);
		}
		
		protected function closeHandler(event:Event=null):void {
			closeThis();
		}
		
		protected function closeThis(needEvent:Boolean=false):void {
			PopUpManager.removePopUp(this);
			if ( needEvent )
				dispatchEvent(new UIDataEvent(UIDataEvent.CLOSE));
		}
	}
}