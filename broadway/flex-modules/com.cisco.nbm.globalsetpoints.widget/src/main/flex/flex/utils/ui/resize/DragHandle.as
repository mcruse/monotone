package flex.utils.ui.resize
{
	import flash.events.Event;
	import flash.filters.DropShadowFilter;
	
	import flex.utils.ui.StyleUtils;
	
	import mx.core.UIComponent;
	import mx.styles.CSSStyleDeclaration;
	import mx.styles.StyleManager;

	[Style(name="backgroundColor", type="uint", format="Color", inherit="no")]
	[Style(name="backgroundAlpha", type="Number", inherit="no")]
	[Style(name="dragHandleColor", type="uint", format="Color", inherit="yes")]
	[Style(name="dragHandleAlpha", type="Number", inherit="yes")]
	
	/**
	 * Renders a drag handle by drawing a set of small dots (squares). 
	 * You can either specify an explicit width and height, or you can specify 
	 * the number of rows and columns (the default is 1 column and 4 rows).
	 * You can also choose how big you want the dots to be.
	 * 
	 * There are styles for setting the backgroundColor, backgroundAlpha (0 by default),
	 * dragHandleColor (0x666666 by default) and dragHandleAlpha (1 by default).
	 * 
	 * There is also a dropShadowEnabled property that sets whether a DropShadowFilter
	 * is used (defaults to false).
	 * 
	 * @author Chris Callendar
	 * @date March 4th, 2010
	 */
	public class DragHandle extends UIComponent
	{
		
		private static var classConstructed:Boolean = classConstruct(); 
		private static function classConstruct():Boolean {
			var style:CSSStyleDeclaration = StyleManager.getStyleDeclaration("DragHandle");
            if (!style) {
                style = new CSSStyleDeclaration();
            }
            style.defaultFactory = function():void {
                this.backgroundColor = 0xffffff;
                this.backgroundAlpha = 0;
                this.dragHandleColor = 0x666666;
                this.dragHandleAlpha = 1;
            };
			StyleManager.setStyleDeclaration("DragHandle", style, true);
            return true;
        };
		
		private var _rows:uint = 4;
		private var _cols:uint = 1;
		private var _dotSize:uint = 2;
		private var _keepOnTop:Boolean = false;
		private var _dropShadowEnabled:Boolean = false;
		public const dropShadowFilter:DropShadowFilter = new DropShadowFilter(1, 45, 0xffffff, 0.5, 1, 1);
		
		public function DragHandle() {
			super();
		}
				
		[Inspectable(category="Drag Handle", defaultValue="false")]
		[Bindable("keepOnTopChanged")]
		public function set keepOnTop(value:Boolean):void {
			if (value != _keepOnTop) {
				_keepOnTop = value;
				invalidateDisplayList();
				dispatchEvent(new Event("keepOnTopChanged"));
			}
		}
		
		public function get keepOnTop():Boolean {
			return _keepOnTop;
		}
		
		[Inspectable(category="Drag Handle", defaultValue="false")]
		[Bindable("dropShadowEnabledChanged")]
		public function set dropShadowEnabled(value:Boolean):void {
			if (value != _dropShadowEnabled) {
				_dropShadowEnabled = value;
				this.filters = (value ? [ dropShadowFilter ] : null);
				dispatchEvent(new Event("dropShadowEnabledChanged"));
			}
		}
		
		public function get dropShadowEnabled():Boolean {
			return _dropShadowEnabled;
		}
		
		[Inspectable(category="Resize Handle", defaultValue="0xdddddd")]
		[Bindable("dropShadowColorChanged")]
		public function set dropShadowColor(value:uint):void {
			if (value != dropShadowFilter.color) {
				dropShadowFilter.color = value;
				if (dropShadowEnabled) {
					this.filters = [ dropShadowFilter ];
				}
				dispatchEvent(new Event("dropShadowColorChanged"));
			}
		}
		
		public function get dropShadowColor():uint {
			return dropShadowFilter.color;
		}
		
		[Inspectable(category="Drag Handle", defaultValue="2")]
		[Bindable("dotSizeChanged")]
		public function set dotSize(value:uint):void {
			if (value != _dotSize) {
				_dotSize = value;
				invalidateSize();
				invalidateDisplayList();
				dispatchEvent(new Event("dotSizeChanged"));
			}
		}
		
		public function get dotSize():uint {
			return _dotSize;
		}
		
		[Inspectable(category="Drag Handle", defaultValue="4")]
		[Bindable("rowsChanged")]
		public function set rows(value:uint):void {
			if (value != _rows) {
				_rows = value;
				invalidateSize();
				invalidateDisplayList();
				dispatchEvent(new Event("rowsChanged"));
			}
		}
		
		public function get rows():uint {
			return _rows;
		}
		
		[Inspectable(category="Drag Handle", defaultValue="1")]
		[Bindable("columnsChanged")]
		public function set columns(value:uint):void {
			if (value != _cols) {
				_cols = value;
				invalidateSize();
				invalidateDisplayList();
				dispatchEvent(new Event("columnsChanged"));
			}
		}
		
		public function get columns():uint {
			return _cols;
		}
		
		override protected function measure():void {
			var h:Number = (rows * dotSize) + ((rows + 1) * dotSize);
			var w:Number = (columns * dotSize) + ((columns + 1) * dotSize);
			measuredWidth = w;
			measuredMinWidth = w;
			measuredHeight = h;
			measuredMinHeight = h;
		}
		
		override public function styleChanged(styleProp:String):void {
			super.styleChanged(styleProp);
			
			if ((styleProp == "backgroundColor") || (styleProp == "backgroundAlpha") || 
				(styleProp == "dragHandleColor") || (styleProp == "dragHandleAlpha")) {
				invalidateDisplayList();
			}
		}
		
		public function updateStyles(colorStyle:Object, alphaStyle:Object = null):void {
			if (colorStyle != null) {
				setStyle("dragHandleColor", colorStyle);
			}
			if (alphaStyle != null) {
				setStyle("dragHandleAlpha", alphaStyle);
			} 				
		}
		
		override protected function updateDisplayList(w:Number, h:Number):void {
			super.updateDisplayList(w, h);
			
			if (keepOnTop) {
				bringToFront();
			}
			
			graphics.clear();
			if (enabled && (w > 0) && (h > 0) && (dotSize > 0)) {
				var bg:uint = StyleUtils.getColorStyle(this, "backgroundColor", 0xffffff);
				var bgAlpha:Number = StyleUtils.getAlphaStyle(this, "backgroundAlpha", 0);
				drawBackground(w, h, bg, bgAlpha);
				var color:uint = StyleUtils.getColorStyle(this, "dragHandleColor", 0x666666);
				var alpha:Number = StyleUtils.getAlphaStyle(this, "dragHandleAlpha", 1);
				if (alpha > 0) {
					drawDragHandle(color, alpha);
				}
			}
		}
		
		protected function drawBackground(w:Number, h:Number, color:uint, alpha:Number = 1):void {
			graphics.lineStyle(0, 0, 0);
			graphics.beginFill(color, alpha);
			graphics.drawRect(0, 0, w, h);
			graphics.endFill();
		}
		
		/**
		 * Draws the drag handle.
		 */
		protected function drawDragHandle(color:uint = 0x666666, alpha:Number = 1):void {
			var rowCount:uint = rows;
			var colCount:uint = columns;
			
			// check if an explicit width or height was set, if so then adjust the columns
			if (!isNaN(explicitWidth)) {
				colCount = Math.round((explicitWidth - dotSize)  / (2 * dotSize));
			}
			if (!isNaN(explicitHeight)) {
				rowCount = Math.round((explicitHeight - dotSize) / (2 * dotSize));
			}
			
			var dx:Number, dy:Number;
			for (var col:uint = 0; col < colCount; col++) {
				dx = dotSize + (2 * col * dotSize);
				for (var row:uint = 0; row < rowCount; row++) {
					dy = dotSize + (2 * row * dotSize); 
					drawDot(color, alpha, dx, dy, dotSize, dotSize);
				}
			}
		}
		
		/**
		 * Draws a single (2x2) dot.
		 */
		protected function drawDot(color:uint, alpha:Number, xx:Number, yy:Number, w:Number = 2, h:Number = 2):void {
			graphics.lineStyle(0, 0, 0);	// no border
			graphics.beginFill(color, alpha);
			graphics.drawRect(xx, yy, w, h);
			graphics.endFill();
		}
		
		public function bringToFront():void {
			if (parent) {
				var index:int = parent.getChildIndex(this); 
				if (index != (parent.numChildren - 1)) { 
					parent.setChildIndex(this, parent.numChildren - 1);
				}
			}
		}
		
	}
}