package com.cisco.ui.components.view
{
	import flash.display.DisplayObject;
	import flash.events.MouseEvent;
	
	import mx.collections.ArrayCollection;
	import mx.containers.BoxDirection;
	import mx.containers.Canvas;
	import mx.events.ChildExistenceChangedEvent;

	public class SplitBox extends Canvas
	{
		public var direction:String = "vertical";

		[ArrayElementType("com.cisco.ui.components.view.SplitDivider")]
		private var dividers:ArrayCollection = new ArrayCollection;

		private var dragStartPosition:Number;
		private var dragPresentPosition:Number;
		private var isDragging:Boolean;
		protected var needCalculation:Boolean;
		protected var currentDivider:SplitDivider;
		public var resizeIfRequired:Boolean;
		private var updateSizeFlag:Boolean;
		
		public function SplitBox() {
			super();
			addEventListener(ChildExistenceChangedEvent.CHILD_ADD, childAddHandler);
			addEventListener(ChildExistenceChangedEvent.CHILD_REMOVE, 
						 childRemoveHandler);
		}
		
		private function childAddHandler(event:ChildExistenceChangedEvent):void {
			var child:DisplayObject = event.relatedObject;
			var anIndex:int = getChildIndex(child);
			createDividerAt(anIndex);
			needCalculation = true;
		}
		
		private function childRemoveHandler(event:ChildExistenceChangedEvent):void {
			var child:DisplayObject = event.relatedObject;
		}
		
		private function createDividerAt(index:int):void {
 			var divider:SplitDivider = new SplitDivider(this);
			rawChildren.addChild(divider);
			dividers.addItemAt(divider,index);
		}
		
		public function mouseDownHandler(event:MouseEvent,divider:SplitDivider):void {
			if ( direction == BoxDirection.HORIZONTAL ) {
				dragStartPosition = mouseX;
			} else {
				dragStartPosition = mouseY;
			}
			isDragging = true;
			currentDivider = divider;
			//divider.startDrag();
		}
		
		public function mouseMoveHandler(event:MouseEvent,divider:SplitDivider):void {
			if ( !isDragging )	return;
			if ( direction == BoxDirection.HORIZONTAL ) {
				dragPresentPosition = mouseX;
//				divider.x += dragPresentPosition - dragStartPosition;
				divider.x = mouseX;
			} else {
				dragPresentPosition = mouseY;
//				divider.y += dragPresentPosition - dragStartPosition;
				divider.y = mouseY;
			}
			dragStartPosition = dragPresentPosition;
			divider.positionDefined = true;
			
			needCalculation = true;
			invalidateDisplayList();
		}
		
		public function mouseUpHandler(event:MouseEvent,divider:SplitDivider):void {
			isDragging = false;
			//divider.stopDrag();
			currentDivider = null;
		}
		
		private function calculatePositions():void {
			var offsetValue:Number = 0;
			for ( var i:int = 0; i < numChildren; i++ ) {
				var divider:SplitDivider = dividers.getItemAt(i) as SplitDivider;
				var child:DisplayObject = getChildAt(i);
				if ( !child.visible ) {
					divider.visible = false;
					continue;
				} else {
					divider.visible = true;
				}
				if ( divider == currentDivider ) {
					if ( direction == BoxDirection.HORIZONTAL ) {
						child.x = offsetValue;
						child.width = divider.x - offsetValue;
						offsetValue += child.width +1;
						divider.y = 0;
					} else {
						child.y = offsetValue;
						child.height = divider.y - offsetValue;
						offsetValue += child.height +1;
						divider.x = 0;
					}
				} else {
					if ( direction == BoxDirection.HORIZONTAL ) {
						child.x = offsetValue;
						divider.x = offsetValue + child.width;
						offsetValue += child.width + 1;
						divider.y = 0;
					} else {
						child.y = offsetValue;
						divider.y = offsetValue + child.height;
						offsetValue += child.height + 1;
						divider.x = 0;
					}
				}
			}
			
			if ( direction == BoxDirection.HORIZONTAL ) {
				updateSizeFlag = true;
				maxWidth = offsetValue;
				width = offsetValue;
			} else {
				updateSizeFlag = true;
				maxHeight = offsetValue;
				height = offsetValue;
			}
			invalidateSize();
		}
		
		override protected function measure():void {
			super.measure();
			if ( updateSizeFlag ) {
				updateSizeFlag = false;
				if ( direction == BoxDirection.HORIZONTAL ) {
					minWidth = maxWidth;
				} else {
					minHeight = maxHeight;
				}
			}
		}
		
		protected function get contentHeight():Number {
			if ( direction == BoxDirection.VERTICAL )
				return unscaledHeight - dividers.length * 2;
			return unscaledHeight;
		}

		protected function get contentWidth():Number {
			if ( direction == BoxDirection.HORIZONTAL )
				return unscaledWidth - dividers.length * 2;
			return unscaledWidth;
		}

		
		override protected function updateDisplayList(unscaledWidth:Number, unscaledHeight:Number):void {
			super.updateDisplayList(unscaledWidth,unscaledHeight);
			
			if ( needCalculation ) {
				needCalculation = false;
				calculatePositions();
			}

			for ( var i:int = 0; i < numChildren; i++ ) {
				var divider:SplitDivider = dividers.getItemAt(i) as SplitDivider;
				var child:DisplayObject = getChildAt(i);
				if ( direction == BoxDirection.HORIZONTAL ) {
					child.y = 0;
					child.height = unscaledHeight;
					divider.y = 0;
					divider.height = unscaledHeight;
				} else {
					child.x = 0;
					child.width = unscaledWidth;
					divider.x = 0;
					divider.width = unscaledWidth;
				}
			}
		}
		
	}
}