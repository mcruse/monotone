package com.cisco.ui.components.view
{
	import flash.events.MouseEvent;
	
	import mx.containers.BoxDirection;
	import mx.containers.Canvas;
	import mx.managers.CursorManager;

	public class SplitDivider extends Canvas
	{
		private var direction:String;
		public var positionDefined:Boolean;
		private var cursorId:int = CursorManager.NO_CURSOR;
		
		[Embed(source="assets/cursor-col-resize.jpg")]
		public static const horizontalResizeIcon:Class;

		[Embed(source="assets/cursor_mac_size_up_down.png")]
		public static const verticalResizeIcon:Class;

		public function SplitDivider(owner:SplitBox)
		{
			super();
			this.owner = owner;
			this.direction = owner.direction as String;
			setStyle("borderStyle","solid");
			setStyle("backgroundColor",0x000000);
			addEventListener(MouseEvent.MOUSE_DOWN,mouseDownHandler);
			addEventListener(MouseEvent.MOUSE_OVER,mouseOverHandler);
			addEventListener(MouseEvent.MOUSE_MOVE,mouseOverHandler);
			addEventListener(MouseEvent.MOUSE_OUT,mouseOutHandler);
		}
		
		protected function mouseOverHandler(event:MouseEvent):void {
			setResizeCursor(true);
		}
		
		protected function mouseOutHandler(event:MouseEvent):void {
			setResizeCursor(false);
		}
		
		override protected function measure():void {
			super.measure();
			if ( direction == BoxDirection.HORIZONTAL ) {
				maxWidth = 2;
			} else {
				maxHeight = 2;
			}
		}
		
		protected function mouseDownHandler(event:MouseEvent):void {
			setResizeCursor(true);
			systemManager.getSandboxRoot().addEventListener(MouseEvent.MOUSE_MOVE, mouseMoveHandler);
			systemManager.getSandboxRoot().addEventListener(MouseEvent.MOUSE_UP, mouseUpHandler);
			//this.owner.addEventListener(MouseEvent.MOUSE_MOVE,mouseMoveHandler);
			//this.owner.addEventListener(MouseEvent.MOUSE_UP,mouseUpHandler);
			(owner as SplitBox).mouseDownHandler(event,this);
		}
		
		protected function mouseMoveHandler(event:MouseEvent):void {
			setResizeCursor(true);
			(owner as SplitBox).mouseMoveHandler(event,this);
		}
		
		protected function mouseUpHandler(event:MouseEvent):void {
			setResizeCursor(false);
			(owner as SplitBox).mouseUpHandler(event,this);
			systemManager.getSandboxRoot().removeEventListener(MouseEvent.MOUSE_MOVE, mouseMoveHandler);
			systemManager.getSandboxRoot().removeEventListener(MouseEvent.MOUSE_UP, mouseUpHandler);
			//this.owner.removeEventListener(MouseEvent.MOUSE_MOVE,mouseMoveHandler);
			//this.owner.removeEventListener(MouseEvent.MOUSE_UP,mouseUpHandler);
		}
		
		private function setResizeCursor(flag:Boolean=true):void {
			if ( flag ) {
				if ( direction == BoxDirection.HORIZONTAL )
					CursorManager.setCursor(horizontalResizeIcon,2,-10,-10);
				else
					CursorManager.setCursor(verticalResizeIcon,2,-8,-8.5);
			} else {
				CursorManager.removeAllCursors();
			}
		}
		
		
	}
}