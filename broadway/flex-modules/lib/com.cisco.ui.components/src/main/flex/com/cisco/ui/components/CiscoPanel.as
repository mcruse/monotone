package com.cisco.ui.components
{
	import flash.events.Event;
	import flash.events.MouseEvent;
	
	import mx.containers.Panel;
	import mx.controls.Button;
	import mx.core.IFlexDisplayObject;
	import mx.events.FlexEvent;
	import mx.styles.CSSStyleDeclaration;
	import mx.styles.StyleManager;

	public class CiscoPanel extends Panel
	{
		private var resizeHandleSkin:IFlexDisplayObject;
		
		public function CiscoPanel()
		{
			super();
			addEventListener(FlexEvent.CREATION_COMPLETE, internal_handleCreationComplete);
			
			addEventListener(MouseEvent.MOUSE_DOWN, handleMouseDown);
			addEventListener(RESIZE_CLICK, handleClickResize);
		}
		
		
		public function internal_handleCreationComplete(event:Event):void {
			var declaration:CSSStyleDeclaration = StyleManager.getStyleDeclaration("CiscoPanel");

			if (declaration == null) {
				return;
			}
			
			var resizeHandleSkinClass:Class = declaration.getStyle("resizeHandleSkin");
			 
			if (resizeHandleSkinClass == null) {
				return;
			}	
			
			resizeHandleSkin = IFlexDisplayObject(new resizeHandleSkinClass());	
			resizeHandleSkin.name = "resizeHandleSkin";
			
			//addChild(DisplayObject(resizeHandleSkin));
		}
		public static const RESIZE_CLICK:String = "resizeClick";
			
		protected function handleMouseDown(event:MouseEvent):void{
			 	var llx:Number = x + width;
			 	var lly:Number = y + height;
			 	
			 	var ulx:Number = llx-7;
			 	var uly:Number = lly-7; // TODO Make consts
			 	
			 	var panelRelX:Number = event.stageX;
			 	var panelRelY:Number = event.stageY;
			 	
//			 	var panelRelX:Number = event.localX + x;
//			 	var panelRelY:Number = event.localY + y;
			 	
			 	if (ulx <= panelRelX && panelRelX <= llx) {
			 		if (uly <= panelRelY && panelRelY <= lly) {
			 			event.stopPropagation();
			 			var newEvent:MouseEvent = new MouseEvent(RESIZE_CLICK, true);
			 			
			 			newEvent.localX = event.stageX;
			 			newEvent.localY = event.stageY;
			 			
			 			dispatchEvent(newEvent);
			 		}
			 	}
		}
		
		private var initX:int;
		
		private var initY:int;
		
		private function handleClickResize(event:MouseEvent):void {
			initX = event.localX;
			initY = event.localY;
			
			systemManager.addEventListener(MouseEvent.MOUSE_MOVE, 
				handleMouseMove);
			systemManager.addEventListener(MouseEvent.MOUSE_UP,
				handleMouseUp);
		}
		
		private function handleMouseMove(event:MouseEvent):void {
			
			event.stopImmediatePropagation();
			
			var newWidth:Number = width + (event.stageX - initX);
			var newHeight:Number = height + (event.stageY - initY);
			
			if (newHeight >= minHeight) {
				height = newHeight;
				initY = event.stageY;
			}
			
			if (newWidth >= minWidth) {
				width = newWidth;
				initX = event.stageX;
			}
		}
		
		private function handleMouseUp(event:MouseEvent):void {
			event.stopImmediatePropagation();
			
			systemManager.removeEventListener(MouseEvent.MOUSE_MOVE, 
				handleMouseMove);
			systemManager.removeEventListener(MouseEvent.MOUSE_UP,
				handleMouseUp);
		}
	
		
		/*	
		override protected function updateDisplayList(unscaledWidth:Number, unscaledHeight:Number):void
		{
			super.updateDisplayList(unscaledWidth, unscaledHeight);
		}
		*/
		
	}
}