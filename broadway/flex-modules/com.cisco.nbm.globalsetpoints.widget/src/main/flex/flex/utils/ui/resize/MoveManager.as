package flex.utils.ui.resize
{
	import flash.events.Event;
	import flash.events.MouseEvent;
	import flash.geom.Rectangle;
	
	import mx.controls.Button;
	import mx.core.Container;
	import mx.core.EdgeMetrics;
	import mx.core.UIComponent;
	import mx.managers.CursorManager;

	/**
	 * Similar to the ResizeManager, this class adds support for moving a component by dragging it
	 * with the mouse. It also supports showing a custom cursor while dragging.
	 * 
	 * @author Chris Callendar
	 * @date March 17th, 2009
	 */ 
	public class MoveManager
	{
		
		private var _moveHandleWidth:uint = 6;
		private var _moveHandleHeight:uint = 16;	//14
		
		private var _moveHandle:DragHandle;
		
		// the component that is being moved
		private var moveComponent:UIComponent;
		// the component that when dragged causes the above component to move
		private var dragComponent:UIComponent;
		// the component that the move handle is added to
		private var moveHandleParent:UIComponent;
		
		private var dragging:Boolean;
		private var _enabled:Boolean;
		private var _bringToFrontOnMove:Boolean;
		private var _constrainToParentBounds:Boolean;
		private var _constrainToBounds:Rectangle;
		
		[Embed(source="/assets/cursor_move.gif")]
		public var moveIcon:Class;
		private var moveCursorID:int;
		
		public function MoveManager() {
			dragging = false;
			_enabled = true;
			_bringToFrontOnMove = false;
			_constrainToParentBounds = false;
			_constrainToBounds = null;
			moveCursorID = 0;
		}
		
		public function get moveHandleHeight():uint {
			return _moveHandleHeight;
		}
		
		public function set moveHandleHeight(value:uint):void {
			if (value != _moveHandleHeight) {
				_moveHandleHeight = value;
				if (_moveHandle) {
					_moveHandle.height = value;
				}
				if (moveComponent) {
					moveComponent.invalidateDisplayList();
				}
				if (dragComponent) {
					dragComponent.invalidateDisplayList();
				}
			}
		}
		
		public function get moveHandleWidth():uint {
			return _moveHandleWidth;
		}
		
		public function set moveHandleWidth(value:uint):void {
			if (value != _moveHandleWidth) {
				_moveHandleWidth = value;
				if (_moveHandle) {
					_moveHandle.width = value;
				}
				if (moveComponent) {
					moveComponent.invalidateDisplayList();
				}
				if (dragComponent) {
					dragComponent.invalidateDisplayList();
				}
			}
		}
		
		public function get enabled():Boolean {
			return _enabled;
		}
		
		public function set enabled(en:Boolean):void {
			if (en != _enabled) {
				_enabled = en;
				moveHandle.enabled = en;
				moveHandle.visible = en;
			}
		}
		
		public function get bringToFrontOnMove():Boolean {
			return _bringToFrontOnMove;
		}
		
		public function set bringToFrontOnMove(value:Boolean):void {
			_bringToFrontOnMove = value;
		}
		
		/**
		 * Returns true if the component's movement is constrained to within
		 * the parent's bounds.
		 */
		public function get constrainToParentBounds():Boolean {
			return _constrainToParentBounds;
		}
		
		/**
		 * Set to true if the component's movement is to be constrained to within
		 * the parent's bounds.
		 */
		public function set constrainToParentBounds(value:Boolean):void {
			_constrainToParentBounds = value;
		}
		
		/**
		 * Returns the bounds used to constrain the component's movement.
		 */
		public function get constrainToBounds():Rectangle {
			return _constrainToBounds;
		}
		
		/**
		 * Sets the bounds used to constrain the component's movement.
		 */
		public function set constrainToBounds(value:Rectangle):void {
			_constrainToBounds = value;
		}
		
		/**
		 * Adds support for moving a component.
		 * @param moveComponent the component that will have its x and y values changed
		 * @param dragComponent the component that will have a mouse_down listener added to listen
		 *  for when the user drags it.  If null then the moveComponent is used instead.
		 * @param moveHandleParent the parent component which will have the move handle added to it.
		 */
		public function addMoveSupport(moveComponent:UIComponent, dragComponent:UIComponent = null, 
									   moveHandleParent:UIComponent = null):void {
			this.moveComponent = moveComponent;
			this.dragComponent = dragComponent;
			this.moveHandleParent = moveHandleParent;
			
			if (moveHandleParent) {
				moveHandleParent.addChildAt(moveHandle, 0);
			}
			if (dragComponent) {
				dragComponent.addEventListener(MouseEvent.MOUSE_DOWN, dragComponentMouseDown);
			} else if (moveComponent) {
				moveComponent.addEventListener(MouseEvent.MOUSE_DOWN, dragComponentMouseDown);
			}
		}

		/**
		 * Removes move support, removes the mouse listener and the move handle.
		 */ 
		public function removeMoveSupport():void {
			if (dragComponent) {
				dragComponent.removeEventListener(MouseEvent.MOUSE_DOWN, dragComponentMouseDown);
			} else if (moveComponent) {
				moveComponent.removeEventListener(MouseEvent.MOUSE_DOWN, dragComponentMouseDown);
			}
			if (moveHandleParent && _moveHandle) {
				moveHandleParent.removeChild(moveHandle);
			}
		}

		/**
		 * Returns the move handle component.
		 */
		public function get moveHandle():DragHandle {
			if (_moveHandle == null) {
				_moveHandle = new DragHandle();
				_moveHandle.width = moveHandleWidth;
				_moveHandle.height = moveHandleHeight;
				_moveHandle.dropShadowEnabled = true;
			}
			return _moveHandle;
		}
		
//		/**
//		 * Draws a 6x14 move/drag handle.
//		 */
//		public function drawMoveHandle(parentW:Number, parentH:Number, color:uint = 0x666666, alpha:Number = 1):void {
//			if (enabled) {
//				var g:Graphics = moveHandle.graphics;
//				g.clear();
//				var xx:int = 2;
//				var yy:int = 2;
//				var numDots:int = int(Math.floor(moveHandleHeight / 4));
//				for (var i:int = 0; i < numDots; i++) {
//					drawDot(g, color, alpha, xx, yy + (i * 4));
//					//drawDot(g, color, alpha, xx + 4, yy + (i * 4));
//				}
//			}
//		}
//		
//		/**
//		 * Draws a single (2x2) dot.
//		 */
//		private function drawDot(g:Graphics, color:uint, alpha:Number, xx:Number, yy:Number, w:Number = 2, h:Number = 2):void {
//			g.lineStyle(0, 0, 0);
//			g.beginFill(color, alpha);
//			g.drawRect(xx, yy, w, h);
//			g.endFill();
//		}
		
		/**
		 * This function gets called when the user presses down the mouse button on the
		 * dragComponent (or if not specified then the moveComponent).
		 * It starts the drag process.
		 */
		private function dragComponentMouseDown(event:MouseEvent):void {
			if (!enabled) {
				return;
			}
			// special case - ignore if the target is a button (e.g. close button)
			if ((event.target is Button) && (event.target != dragComponent)) {
				return;
			}

			// move above all others
			if (bringToFrontOnMove && moveComponent.parent) {
				var index:int = moveComponent.parent.getChildIndex(moveComponent);
				var last:int = moveComponent.parent.numChildren - 1;
				if (index != last) {
					moveComponent.parent.setChildIndex(moveComponent, last);
				}
			}
			
			// Constain the movement by the parent's bounds?
			var bounds:Rectangle = null;
			if (constrainToBounds != null) {
				bounds = constrainToBounds;
			} else if (constrainToParentBounds && moveComponent.parent) {
				bounds = moveComponent.parent.getBounds(moveComponent.parent);
				// need to reduce the size by the component's width/height
				bounds.width = Math.max(0, bounds.width - moveComponent.width);
				bounds.height = Math.max(0, bounds.height - moveComponent.height);
				
				// adjust for the border (e.g. on a Panel)
				if (moveComponent.parent is Container) {
					var p:Container = (moveComponent.parent as Container);
					var bm:EdgeMetrics = p.borderMetrics;
					bounds.width = Math.max(0, bounds.width - bm.left - bm.right);
					bounds.height = Math.max(0, bounds.height - bm.top - bm.bottom);
				}
			}
			moveComponent.startDrag(false, bounds);
			setMoveCursor();
			moveComponent.systemManager.addEventListener(MouseEvent.MOUSE_MOVE, dragComponentMove);
			moveComponent.systemManager.addEventListener(MouseEvent.MOUSE_UP, dragComponentMouseUp);
			moveComponent.systemManager.stage.addEventListener(Event.MOUSE_LEAVE, dragComponentMouseUp);
		}

		private function dragComponentMove(event:MouseEvent):void {
			if (!dragging) {
				dragging = true;
				moveComponent.clearStyle("top");
				moveComponent.clearStyle("right");
				moveComponent.clearStyle("bottom");
				moveComponent.clearStyle("left");
				moveComponent.dispatchEvent(new Event("dragStart"));
			}
			moveComponent.dispatchEvent(new Event("drag"));
		}
		
		private function dragComponentMouseUp(event:Event):void {
			moveComponent.stopDrag();
			removeMoveCursor();
			if (dragging) {
				dragging = false;
				moveComponent.dispatchEvent(new Event("dragEnd"));
			}
			moveComponent.systemManager.removeEventListener(MouseEvent.MOUSE_MOVE, dragComponentMove);
			moveComponent.systemManager.removeEventListener(MouseEvent.MOUSE_UP, dragComponentMouseUp);
			moveComponent.systemManager.stage.removeEventListener(Event.MOUSE_LEAVE, dragComponentMouseUp);
		}	
		
		private function setMoveCursor():void {
			if ((moveCursorID == 0) && (moveIcon != null)) {
				moveCursorID = CursorManager.setCursor(moveIcon, 2, -12, -10);
			}
		}
		
		private function removeMoveCursor():void {
			if (moveCursorID != 0) {
				CursorManager.removeCursor(moveCursorID);
				moveCursorID = 0;
			} 
		} 
		
	}
}