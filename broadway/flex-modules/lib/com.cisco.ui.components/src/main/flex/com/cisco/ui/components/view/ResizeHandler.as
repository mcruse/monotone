package com.cisco.ui.components.view
{
	import com.cisco.ui.components.vo.IDraggable;
	
	import flash.events.MouseEvent;
	import flash.geom.Point;
	
	import mx.core.UIComponent;
	
	public class ResizeHandler
	{
		private var _component:UIComponent;
		private var isDragging:Boolean=false;
		private var isResizing:Boolean=false;
		public var resizeOffset:Number = 5;
		private var resizingCorner:String;
		private var mousePoint:Point;

		public static const LEFT_TOP:String = "leftTop";
		public static const LEFT_MIDDLE:String = "leftMiddle";
		public static const LEFT_BOTTOM:String = "leftBottom";
		public static const TOP_MIDDLE:String = "topMiddle";
		public static const RIGHT_TOP:String = "rightTop";
		public static const RIGHT_MIDDLE:String = "rightMiddle";
		public static const RIGHT_BOTTOM:String = "rightBottom";
		public static const BOTTOM_MIDDLE:String = "bottomMiddle";
		
		public function ResizeHandler(component:UIComponent=null) {
			this.component = component;
		}
		
		public function get component():UIComponent {
			return this._component;
		}
		
		public function set component(value:UIComponent):void {
			if ( _component ) {
				_component.removeEventListener(MouseEvent.MOUSE_DOWN,mouseDownHandler);
			}
			this._component = value;
			if ( _component ) {
				_component.addEventListener(MouseEvent.MOUSE_DOWN,mouseDownHandler);
			}
		}
		
		protected function mouseDownHandler(event:MouseEvent):void {
			var mouseX:Number = component.mouseX;
			var mouseY:Number = component.mouseY;
			
			var unscaledWidth:Number = component.width;
			var unscaledHeight:Number = component.height;
			
			isResizing = false;
			isDragging = false;
			
			if ( mouseX >= 0 && mouseX <= resizeOffset ) {
				isResizing = true;
				if ( mouseY >= 0 && mouseY <= resizeOffset ) {
					resizingCorner = LEFT_TOP;
				} else if ( mouseY >= unscaledHeight - resizeOffset) {
					resizingCorner = LEFT_BOTTOM;
				} else {
					resizingCorner = LEFT_MIDDLE;
				}
			} else if ( mouseX >= unscaledWidth - resizeOffset ) {
				isResizing = true;
				if ( mouseY >= 0 && mouseY <= resizeOffset ) {
					resizingCorner = RIGHT_TOP;
				} else if ( mouseY >= unscaledHeight - resizeOffset) {
					resizingCorner = RIGHT_BOTTOM;
				} else {
					resizingCorner = RIGHT_MIDDLE;
				}
			} else if ( mouseY <= resizeOffset ) {
				isResizing = true;
				resizingCorner = TOP_MIDDLE;
			} else if ( mouseY >= unscaledHeight - resizeOffset ) {
				isResizing = true;
				resizingCorner = BOTTOM_MIDDLE;
			} else if ( component is IDraggable && (component as IDraggable).isDraggableArea(new Point(mouseX,mouseY)) ) {
				isDragging = true;
			}
			
			if ( isResizing || isDragging ) {
				component.addEventListener(MouseEvent.MOUSE_MOVE,mouseMoveHandler);
				component.addEventListener(MouseEvent.MOUSE_UP,mouseUpHandler);
				mousePoint = new Point(mouseX,mouseY);
			}
		}
		
		protected function mouseMoveHandler(event:MouseEvent):void {
			if ( isDragging )
				component.startDrag();
			else if ( isResizing ) {
				var mousePresentPoint:Point = new Point(component.mouseX,component.mouseX);//component.mouseX,component.mouseY);
				var draggedDistanceX:Number;
				var draggedDistanceY:Number;
				if ( mousePoint != null ) {
					draggedDistanceX = - mousePresentPoint.x + mousePoint.x;
					draggedDistanceY = - mousePresentPoint.y + mousePoint.y;
				}
				
				switch (resizingCorner) {
					case LEFT_TOP :
						component.x -= draggedDistanceX;
						component.y -= draggedDistanceY;
						component.width += draggedDistanceX;
						component.height += draggedDistanceY;
						break;
					case LEFT_MIDDLE :
						component.x -= draggedDistanceX;
						component.width += draggedDistanceX;
						break;
					case LEFT_BOTTOM :
						component.x -= draggedDistanceX;
						component.width += draggedDistanceX;
						component.height -= draggedDistanceY;
						break;
					case TOP_MIDDLE :
						component.y -= draggedDistanceY;
						component.height += draggedDistanceY;
						break;
					case RIGHT_TOP :
						component.y -= draggedDistanceY;
						component.width -= draggedDistanceX;
						component.height += draggedDistanceY;
						break;
					case RIGHT_MIDDLE :
						component.width -= draggedDistanceX;
						break;
					case RIGHT_BOTTOM :
						component.width -= draggedDistanceX;
						component.height -= draggedDistanceY;
						break;
					case BOTTOM_MIDDLE :
						component.height -= draggedDistanceY;
						break;
				}
				//mousePoint = mousePresentPoint;
			}
		}
			
		protected function mouseUpHandler(event:MouseEvent):void {
			if ( isDragging ) {
				component.stopDrag();
				isDragging = false;
			}
			component.removeEventListener(MouseEvent.MOUSE_OVER,mouseMoveHandler);
			component.removeEventListener(MouseEvent.MOUSE_MOVE,mouseMoveHandler);
			component.removeEventListener(MouseEvent.MOUSE_UP,mouseUpHandler);
			isResizing = false;
		}
	}
}