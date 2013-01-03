package flex.utils.ui.resize
{
	import flash.display.InteractiveObject;
	import flash.events.Event;
	
	import mx.controls.Button;
	import mx.core.UIComponent;
	import mx.styles.CSSStyleDeclaration;
	import mx.styles.StyleManager;
	
	/** 
	 * Dispatched when this component starts being dragged.
	 */
	[Event(name="dragStart", type="flash.events.Event")]

	/** 
	 * Dispatched when this component is being dragged. 
	 */
	[Event(name="drag", type="flash.events.Event")]

	/** 
	 * Dispatched when this component stops being dragged. 
	 */
	[Event(name="dragEnd", type="flash.events.Event")]

	/**
	 * Fired when the panel is about to start resizing. 
	 */
	[Event(name="resizeStart", type="mx.events.ResizeEvent")]

	/**
	 * Fired when the panel has finished resizing.
	 */
	[Event(name="resizeEnd", type="mx.events.ResizeEvent")]

	/**
	 *  The alpha value for the resize handle.
	 *  @default 0x666666
	 */
	[Style(name="resizeHandleColor", type="Color", inherit="no")]

	/**
	 *  The alpha value for the resize handle.
	 *  @default 1
	 */
	[Style(name="resizeHandleAlpha", type="Number", inherit="no")]

	/**
	 *  The alpha value for the move handle.
	 *  @default 0x666666
	 */
	[Style(name="moveHandleColor", type="Color", inherit="no")]

	/**
	 *  The alpha value for the move handle.
	 *  @default 1
	 */
	[Style(name="moveHandleAlpha", type="Number", inherit="no")]

	/**
	 * Extends the Button class to let the user resize the button by dragging on a small
	 * 16x16 resize handle in the bottom right corner of the button.  Also has support
	 * for adding a move handle too for moving the button around (requires that this button's
	 * parent is a Canvas or similar container with no layout).
	 * 
	 * See the ResizeManager class for more details.
	 * 
	 * You can also specify the minWidth, minHeight, maxWidth, and maxHeight properties
	 * to restrict the size of the button.
	 * 
	 * If movable is set to true then you can choose to constrain the button's movement
	 * to the button's parent's bounds.  Or you can specify a custom Rectangle to use when
	 * constaining the button's movement.
	 * 
	 *  <pre>
 	 *  &lt;ResizableButton
	 *   <strong>Styles</strong>
	 *   resizeHandleColor="0x666666"
	 *   resizeHandleAlpha="1"
	 *   moveHandleColor="0x666666"
	 *   moveHandleAlpha="1"
	 * &gt;
 	 *      ...
 	 *      <i>child tags</i>
 	 *      ...
 	 *  &lt;/ui:ResizableButton&gt;
 	 *  </pre>
 	 * 
	 * @author Chris Callendar
	 * @date March 17th, 2009
	 */
	public class ResizableButton extends Button
	{
		// setup the default styles
		private static var classConstructed:Boolean = classConstruct(); 
		private static function classConstruct():Boolean {
            var style:CSSStyleDeclaration = StyleManager.getStyleDeclaration("ResizableButton"); 
            if (!style) {
                style = new CSSStyleDeclaration();
            }
            style.defaultFactory = function():void {
               	this.resizeHandleColor = 0x0;
                this.resizeHandleAlpha = 1;
                this.moveHandleColor = 0x0;
                this.moveHandleAlpha = 1;
            };
			StyleManager.setStyleDeclaration("ResizableButton", style, true);
            return true;
        };
        		
		private var _resizeManager:ResizeManager;
		private var _moveManager:MoveManager;
		private var _dragComponent:UIComponent;
		private var _addDragHandle:Boolean;
		
		private var addedMoveSupport:Boolean;
		private var createdChildren:Boolean;
		
		public function ResizableButton(canResize:Boolean = true, canMove:Boolean = false) {
			super();
			this._resizeManager = new ResizeManager(this);
			this._moveManager = new MoveManager();
			this.resizable = canResize;
			this.movable = canMove;
			this._addDragHandle = true;
			// required for the resize handle to be draggable
			this.mouseChildren = true;
			addEventListener(Event.ADDED, childAdded);
			
			// set a minimum size for this button
			minWidth = 24;
			minHeight = 24;
		}
		
		private function childAdded(event:Event):void {
			// Disable mouse events for all children except the resize and move handles
			for (var i:int = 0; i < numChildren; i++) {
				var child:InteractiveObject = (getChildAt(i) as InteractiveObject);
				if (child && (child != resizeManager.resizeHandle) && (child != moveManager.moveHandle)) {
					child.mouseEnabled = false;
				}
			}
		}

		public function get moveManager():MoveManager {
			return _moveManager;
		}
		
		public function get resizeManager():ResizeManager {
			return _resizeManager;
		}
				
		[Inspectable(category="Resize")]
		public function get resizable():Boolean {
			return resizeManager.enabled;
		}
		
		public function set resizable(canResize:Boolean):void {
			resizeManager.enabled = canResize;
			if (canResize) {
				// looks better for the resize handle
				setStyle("roundedBottomCorners", false);
			}
		}	
		
		[Inspectable(category="Resize")]
		public function get movable():Boolean {
			return moveManager.enabled;
		}
		
		public function set movable(canMove:Boolean):void {
			if (canMove != moveManager.enabled) {
				moveManager.enabled = canMove;
				if (canMove) {
					addMoveSupport();
				} else {
					removeMoveSupport();
				}
				invalidateDisplayList();
			}
		}
		
		/**
		 * If set to true then when this button is moved it will be put on top
		 * of the other children of this button's parent.
		 */
		[Inspectable(category="Resize", defaultValue="false")]
		public function get bringToFrontOnMove():Boolean {
			return moveManager.bringToFrontOnMove;
		}
		
		public function set bringToFrontOnMove(value:Boolean):void {
			moveManager.bringToFrontOnMove = value;
		}

		/**
		 * If set to true then when this button is resized it will be put on top
		 * of the other children of this button's parent.
		 * Obviously this is only useful when the parent uses an absolute layout (e.g. Canvas).
		 */
		[Inspectable(category="Resize", defaultValue="false")]
		public function set bringToFrontOnResize(value:Boolean):void {
			resizeManager.bringToFrontOnResize = value;
		}
		
		public function get bringToFrontOnResize():Boolean {
			return resizeManager.bringToFrontOnResize;
		}
		
		/**
		 * Prevents the button from being dragged outside of its parent's bounds.
		 */
		[Inspectable(category="Resize")]
		public function get constrainToParentBounds():Boolean {
			return moveManager.constrainToParentBounds;
		}
		
		public function set constrainToParentBounds(constrain:Boolean):void {
			moveManager.constrainToParentBounds = constrain;
		}
		
		/**
		 * Keeps the width to height aspect ratio fixed for this component when resizing (defaults to false).
		 */
		[Inspectable(category="Resize", defaultValue="false")]
		public function get keepAspectRatio():Boolean {
			return resizeManager.keepAspectRatio;
		}
		
		public function set keepAspectRatio(value:Boolean):void {
			resizeManager.keepAspectRatio = value;
		}
		
		[Inspectable(category="Resize")]
		public function get addDragHandle():Boolean {
			return _addDragHandle;
		}
		
		public function set addDragHandle(addHandle:Boolean):void {
			if (addHandle != _addDragHandle) {
				_addDragHandle = addHandle;
				if (movable) {
					addMoveSupport();
					invalidateDisplayList();
				}
			}
		}
		
		protected function addMoveSupport():void {
			if (createdChildren) {
				removeMoveSupport();
				moveManager.addMoveSupport(this, this, (addDragHandle ? this : null));
				moveManager.moveHandle.x = 4;	// left align
				addedMoveSupport = true;
			}
		}
		
		protected function removeMoveSupport():void {
			if (addedMoveSupport) {
				moveManager.removeMoveSupport();
				addedMoveSupport = false;
			}
		}
		
		override protected function createChildren():void {
			super.createChildren();
			createdChildren = true;
			if (movable) {
				addMoveSupport();
			}
			addChild(resizeManager.resizeHandle);
		}
		
		override public function styleChanged(styleProp:String):void {
			super.styleChanged(styleProp);

			var allStyles:Boolean = (styleProp == null) || (styleProp == "styleName");
 			if (allStyles || (styleProp == "resizeHandleColor") || (styleProp == "resizeHandleAlpha")) {
 				resizeManager.resizeHandle.updateStyles(getStyle("resizeHandleColor"), getStyle("resizeHandleAlpha"));
			}
			// copy the move handle styles over
			if (allStyles || (styleProp == "moveHandleColor") || (styleProp == "moveHandleAlpha")) {
				moveManager.moveHandle.updateStyles(getStyle("moveHandleColor"), getStyle("moveHandleAlpha"));
			}
		}
		
		override protected function updateDisplayList(w:Number, h:Number):void {
			super.updateDisplayList(w, h);
			// keep the move handle vertically aligned in the center
			if (moveManager.moveHandle.visible) {
				moveManager.moveHandle.y = Math.max(0, ((h - moveManager.moveHandle.height)/2)-1);
			}
			if (resizeManager.resizeHandle.visible) {
				// keep the resize handle in the correct location
				resizeManager.resizeHandle.setResizeHandlePosition();
				resizeManager.resizeHandle.bringToFront();
			}
		}
		
	}
}