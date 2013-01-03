package flex.utils.ui.resize
{
	import flex.utils.ui.StyleUtils;
	
	import mx.containers.TitleWindow;
	import mx.core.UIComponent;
	import mx.core.mx_internal;
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

	[IconFile("ResizableWindow.png")]
	
	/**
	 * Extends the TitleWindow class to let the user resize the window by dragging on a small
	 * 16x16 resize handle in the bottom right corner of the window.  Also has support
	 * for adding a move handle too for moving the window around (requires that this window's
	 * parent is a Canvas or similar container with no layout).
	 * 
	 * See the ResizeManager class for more details.
	 * 
	 * You can also specify the minWidth, minHeight, maxWidth, and maxHeight properties
	 * to restrict the size of the window.
	 * 
	 * If movable is set to true then you can choose to constrain the window's movement
	 * to the window's parent's bounds.  Or you can specify a custom Rectangle to use when
	 * constaining the window's movement.
	 * 
	 *  <pre>
 	 *  &lt;ResizableWindow
	 *   <strong>Styles</strong>
	 *   resizeHandleColor="0x666666"
	 *   resizeHandleAlpha="1"
	 *   moveHandleColor="0x666666"
	 *   moveHandleAlpha="1"
	 * &gt;
 	 *      ...
 	 *      <i>child tags</i>
 	 *      ...
 	 *  &lt;/ui:ResizableWindow&gt;
 	 *  </pre>
 	 * 
	 * @author Chris Callendar
	 * @date March 17th, 2009
	 */
	public class ResizableWindow extends TitleWindow
	{
		// setup the default styles
		private static var classConstructed:Boolean = classConstruct(); 
		private static function classConstruct():Boolean {
            var style:CSSStyleDeclaration = StyleManager.getStyleDeclaration("ResizableWindow"); 
            if (!style) {
                style = new CSSStyleDeclaration();
            }
            if (style.getStyle("roundedBottomCorners") == undefined) {
            	style.setStyle("roundedBottomCorners", false);	// looks better with resize handle
            }
            style.defaultFactory = function():void {
               	this.resizeHandleColor = 0x666666;
                this.resizeHandleAlpha = 1;
                this.moveHandleColor = 0x666666;
                this.moveHandleAlpha = 1;
            };
			StyleManager.setStyleDeclaration("ResizableWindow", style, true);
            return true;
        };
        		
		private var _resizeManager:ResizeManager;
		private var _moveManager:MoveManager;
		private var _dragComponent:UIComponent;
		private var _addDragHandle:Boolean;
		
		private var addedMoveSupport:Boolean;
		private var createdChildren:Boolean;
		
		public function ResizableWindow(canResize:Boolean = true, canMove:Boolean = false) {
			super();
			this._resizeManager = new ResizeManager(this);
			this._moveManager = new MoveManager();
			this.resizable = canResize;
			this.movable = canMove;
			this._addDragHandle = true;
			
			// set a minimum size for this window
			minWidth = 24;
			minHeight = 24;
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
		 * If set to true then when this window is moved it will be put on top
		 * of the other children of this window's parent.
		 */
		[Inspectable(category="Resize", defaultValue="false")]
		public function get bringToFrontOnMove():Boolean {
			return moveManager.bringToFrontOnMove;
		}
		
		public function set bringToFrontOnMove(value:Boolean):void {
			moveManager.bringToFrontOnMove = value;
		}

		/**
		 * If set to true then when this window is resized it will be put on top
		 * of the other children of this window's parent.
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
		 * Prevents the window from being dragged outside of its parent's bounds.
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
		public function get dragComponent():UIComponent {
			return _dragComponent;
		}
		
		public function set dragComponent(drag:UIComponent):void {
			_dragComponent = drag;
			if (movable) {
				addMoveSupport();
			}
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
				moveManager.addMoveSupport(this, dragComponent, (addDragHandle ? dragComponent : null));
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
			
			// set the drag component to be the titlebar by default
			if (_dragComponent == null) {
				_dragComponent = titleBar;
			}
			if (movable) {
				addMoveSupport();
			}
			
			rawChildren.addChild(resizeManager.resizeHandle);
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
			
		override protected function layoutChrome(w:Number, h:Number):void {
			super.layoutChrome(w, h);
			
			// position the move handle - the x position defaults to the title textfield's x value
			if (movable && titleTextField && (moveManager.moveHandle.parent == titleBar)) {
				var moveX:Number = titleTextField.x;
				if (mx_internal::titleIconObject != null) {
					// shift the title icon over, and use it's x value for the move handle
					moveX = mx_internal::titleIconObject.x;
					mx_internal::titleIconObject.x += moveManager.moveHandle.width + 4;
				}
				moveManager.moveHandle.move(moveX, titleTextField.y);
				titleTextField.x += moveManager.moveHandle.width + 4;
			}
		}
			
		override protected function updateDisplayList(w:Number, h:Number):void {
			super.updateDisplayList(w, h);
			// keep the resize handle in the correct location
			resizeManager.resizeHandle.setResizeHandlePosition();
		}
		
		override public function validateDisplayList():void {
			super.validateDisplayList();
			// prevent the scrollbars from covering up the resize handle
			// if you have no border padding, then you will want to un-comment this line
			// but by default panels have border padding, so the resize handle isn't covered up by scrollbars 
			//resizeManager.adjustScrollBars(horizontalScrollBar, verticalScrollBar);
    	}
    	
	}
}