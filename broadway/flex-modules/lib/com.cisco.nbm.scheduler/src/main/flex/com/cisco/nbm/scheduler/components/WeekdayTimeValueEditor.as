package com.cisco.nbm.scheduler.components
{
	import com.cisco.nbm.scheduler.DailyEntry;
	import com.cisco.nbm.scheduler.EventMetaData;
	
	import flash.display.DisplayObject;
	import flash.display.GradientType;
	import flash.display.SpreadMethod;
	import flash.display.Sprite;
	import flash.events.Event;
	import flash.events.FocusEvent;
	import flash.events.MouseEvent;
	import flash.geom.Matrix;
	import flash.text.TextField;
	
	import mx.collections.ArrayCollection;
	import mx.controls.Label;
	import mx.controls.TextInput;
	import mx.core.UIComponent;
	import mx.core.UITextField;
	import mx.core.mx_internal;
	import mx.events.CollectionEvent;
	import mx.events.CollectionEventKind;
	import mx.events.ResizeEvent;
	import mx.managers.CursorManager;
	import mx.managers.IFocusManagerComponent;

	[Event(name="change", type="flash.events.Event")]
	[Event(name="itemEditBeginning", type="com.cisco.nbm.scheduler.components.WeekdayTimeValueEditorEvent")]
	[Event(name="itemEditBegin", type="com.cisco.nbm.scheduler.components.WeekdayTimeValueEditorEvent")]
	[Event(name="itemEditEnd", type="com.cisco.nbm.scheduler.components.WeekdayTimeValueEditorEvent")]
	/**
	 * This is a horiontal control for adding time value pairs to a weekday.
	 */
	public class WeekdayTimeValueEditor extends UIComponent implements IFocusManagerComponent
	{
		
		private static const MAIN_CONTROL_MIN_HEIGHT:int = 20;
		
		private static const VERTICAL_SEPARATOR_MIN_HEIGHT:int = 2;
		
		private static const NUMBER_CONTROL_MIN_HEIGHT:int = 5;
		
		private var _entries:ArrayCollection = new ArrayCollection();
		
		private var _selectedEntry:DailyEntry;
		
		private var _selectedIndex:int = -1;
		
		private var _color:int = 0;
		
		private var _entryName:String = "";
		
		public var dayName:String;
		
		/*
		 * This flag is set when the value of "_entries" changes
		 */
		private var entriesChanged:Boolean = false; 
		
		/*
		 * This flag is set when there is a collection change event
		 */
		private var individualEntriesChanged:Boolean = false;
		
		public var debug:Boolean = false;
		
		/**
		 * This is the height of the main box in the middle.  It is calculated
		 * based on summing the separators and the upper and lower number boxes.
		 * 
		 * It has a minimum value of MAIN_CONTROL_MIN_HEIGHT
		 */
		private var mainControlHeight:int = MAIN_CONTROL_MIN_HEIGHT;
		
		private var numberControlHeight:int = NUMBER_CONTROL_MIN_HEIGHT;
		
		private var verticalSeparatorHeight:int = VERTICAL_SEPARATOR_MIN_HEIGHT;
		
		private var pixelToMinuteRatio:Number = 1;
		
		private var hitAreaSprite:Sprite;
		
		private var controlBackgroundColor:uint = 0x6699CC;
		
		private var rectangles:Array = [];
		
		/*
		 * The ID of the cursor for moving left to right
		 */
		private var cursorID:int;
		
		[Embed(source='/assets/horizontal_resize_cursor.png')] 
		private var HORIZONTAL_RESIZE_CURSOR:Class;
		
		private var minTimeInPixels:int = 4;
		
		public var editable:Boolean = true;
		
		public var selectable:Boolean = true;
		
		/*
		 * Temporary variables for holding the rectangle under the mouse, etc
	     */  
		private var currentRectangle:Object = null;
		private var selectionRectangle:Object = null;
		private var dragging:Boolean = false;
		
		/**
		 * Array of labels for the time.  The labels are displayed in the
		 * bottom rectangle below is entry.  
		 */
		private var timeLabels:Array = [];
		
		private var cachedEntryValues:Object = {};
		
		//private var selectedTimeLabel:Label;
		
		private var sizeChanged:Boolean = true;
		
		[Bindable]
		private var _metaData:ArrayCollection;
		
		public function WeekdayTimeValueEditor()
		{
			super();
			doubleClickEnabled = true;
			focusEnabled = true;
			
			addEventListener(MouseEvent.MOUSE_MOVE, handleMouseMove);
			addEventListener(MouseEvent.MOUSE_DOWN, handleMouseDown);
			addEventListener(MouseEvent.MOUSE_UP, handleMouseUp);
			addEventListener(ResizeEvent.RESIZE, handleResize);
			addEventListener(MouseEvent.ROLL_OUT, handleRollOut);
			//addEventListener(FocusEvent.FOCUS_OUT, handleFocusChange);
			addEventListener(FocusEvent.MOUSE_FOCUS_CHANGE, handleMouseFocusChange);
			addEventListener(FocusEvent.FOCUS_IN, handleFocusIn);
			addEventListener(FocusEvent.FOCUS_OUT, handleFocusOut);
		}
		
		/**
		 * Updates the meta data
		 */
		public function set metaData(value:ArrayCollection):void
		{
			if (value != _metaData)
			{
				_metaData = value;
				entriesChanged = true;
				invalidateProperties();
			}
		}
		
		private function handleMouseFocusChange(event:FocusEvent):void
		{
		}
		
		private function handleFocusChange(event:FocusEvent):void
		{
			//selectedEntry = null;
		}
		
		private function handleFocusIn(event:FocusEvent):void
		{
		}
		
		private function handleFocusOut(event:FocusEvent):void
		{
			//selectedEntry = null;
		}
		
		private function handleResize(event:ResizeEvent):void
		{
			pixelToMinuteRatio = width / 1440.0; // 1440 = 24 hours * 60 minutes
			calculateEntryRectangles();
			invalidateDisplayList();
		}
		
		public function get entries():ArrayCollection
		{
			return _entries;
		}
		
		public function set entries(value:ArrayCollection):void
		{
			if (value === _entries)
			{
				return;
			}
			
			detachEntriesListeners(_entries);
			_entries = value;
			attachEntriesListeners(_entries);
			
			entriesChanged = true;
			
			invalidateProperties();	
			invalidateDisplayList();
		}
		
		
		public function set selectedEntry(value:DailyEntry):void
		{
			if (value !== _selectedEntry)
			{
				_selectedEntry = value;
				_selectedIndex = _entries.getItemIndex(_selectedEntry);
				
				invalidateProperties();
				invalidateDisplayList();
			}
		}
		
		public function get selectedEntry():DailyEntry
		{
			return _selectedEntry;
		}
		
		public function set selectedIndex(value:int):void
		{
			if (value !== _selectedIndex)
			{
				if (value >= _entries.length)
				{
					throw new Error("Invalid index " + value + ", max value is: " + _entries.length);
				}
				
				_selectedIndex = value;
				
				if (_selectedIndex < 0)
				{
					_selectedEntry = null;
				} 
				else 
				{
					_selectedEntry = _entries.getItemAt(_selectedIndex) as DailyEntry;
				}
				
				invalidateProperties();
				invalidateDisplayList();
			}
		}
		
		public function get selectedIndex():int
		{
			return _selectedIndex;
		}
		
		override protected function commitProperties():void
		{
			super.commitProperties();
			
			if (entriesChanged)
			{
				entriesChanged = false;
				removeEntryLabels();
				calculateEntryRectangles();
			}
			
			if (individualEntriesChanged)
			{
				individualEntriesChanged = false;
				updateEntryRectangles();
			}
		}
		
		public function set color(value:int):void
		{
			_color = value;
			invalidateDisplayList();
		}
		
		public function get color():int
		{
			return _color;
		}
		
		public function set entryName(value:String):void
		{
			_entryName = value;
			calculateEntryRectangles();
			invalidateDisplayList();
		}
		
		private function removeEntryLabels():void
		{
			for (var entry:Object in cachedEntryValues)
			{
				var label:DisplayObject = cachedEntryValues[entry];
				removeChild(label);
			}
			
			cachedEntryValues = {};
		}
		
		private function calculateEntryRectangles():void
		{
			
			rectangles.splice(0, rectangles.length);
			
			var edge:Number = width;
			
			if (_entries != null)
			{
				var tempX:Number = 0;
				var rectWidth:Number = 0;
				
				for (var i:int = _entries.length-1; i >= 0; i--)
				{
					var entry:DailyEntry = _entries.getItemAt(i) as DailyEntry;
					
					tempX = Math.floor((entry.time / 60) * pixelToMinuteRatio);
					
					rectWidth = Math.floor(edge - tempX);
					edge = tempX;
					
					var rect:Object = { x : tempX, width : rectWidth, 
						entry : entry, label : null }
					
					if (cachedEntryValues[entry] == null)
					{
						// Now add the label
						var label:TextField = new TextField();
						
						label.text = "";
						
						label.mouseEnabled = false;
						label.x = tempX;
						label.y = numberControlHeight + verticalSeparatorHeight;// + (label.height / 2);
						addChild(label);
						
						cachedEntryValues[entry] = label;
						
						rect.label = label;
					}
					else
					{
						rect.label = cachedEntryValues[entry];
					}

					// TODO Cache this
					if (_entryName != null)
					{
						rect.label.text = new String(_entryName);
					}
					else
					{
						rect.label.text = "";
					}
					
					// Resize the label
					if (rect.label.width > rect.width)
					{
						rect.label.width = rect.width - 5;
					} 
					
					rectangles.push(rect);
				}
				
				// reverse
				rectangles.reverse();
			}
			
			updateEntryLabelSizes();
		}
		
		private function updateEntryRectangles():void
		{
			var edge:Number = width;
			
			var tempX:Number = 0;
				var rectWidth:Number = 0;
			
			rectangles.reverse();	
			for each (var rect:Object in rectangles)
			{
				var entry:DailyEntry = rect.entry;
				
				tempX = Math.floor((entry.time / 60) * pixelToMinuteRatio);
				
				rectWidth = Math.floor(edge - tempX);
				edge = tempX;
				
				rect.x = tempX;
				rect.width = rectWidth;			
			}
			rectangles.reverse();
			
		}
		
		override protected function measure():void
		{
			super.measure();
			
			measuredMinWidth = 100;
			measuredMinHeight = (verticalSeparatorHeight * 2) + 
				(numberControlHeight*2)  + 10 + 5; // + mainControlHeight;
				// TODO Determine why we need to dad 2
				
			measuredHeight = measuredMinHeight;
			measuredWidth = measuredMinWidth;
			
		}
		
		override protected function updateDisplayList(unscaledWidth:Number, unscaledHeight:Number):void
		{
			super.updateDisplayList(unscaledWidth, unscaledHeight);
			
			var tempY:Number = 0; 
			var tempX:Number = 0;
			
			graphics.clear();
			
			// debug
			//graphics.lineStyle(1, 0xff0000);
			//graphics.drawRect(0, 0, width, height);
			
			graphics.lineStyle(0, 0, 0);
			graphics.beginFill(controlBackgroundColor, 1);
			graphics.drawRect(0, numberControlHeight + verticalSeparatorHeight, 
				width, mainControlHeight);
			graphics.endFill();
			
			graphics.lineStyle(0, 0xffffff, 0.4);
			tempY = numberControlHeight + verticalSeparatorHeight;
			graphics.moveTo(0, tempY + mainControlHeight);
			graphics.lineTo(width, tempY + mainControlHeight);
			graphics.lineTo(width, tempY);
			
			graphics.lineStyle(0, 0, 0.4);
			graphics.moveTo(0, tempY + mainControlHeight);
			graphics.lineTo(0, tempY);
			graphics.lineTo(width, tempY);
			
			tempY = 0;
			
			
			if (sizeChanged)
			{
				sizeChanged = false;
			}
			
			// Draw the boxes for debug purposes
			if (debug)
			{
				graphics.lineStyle(1, 0xff00ff);
				
				// Draw the top control box ...
				graphics.drawRect(0, 0, width, numberControlHeight);
				
				// Skip the gutter
				
				// Draw the main control box
				graphics.drawRect(0, numberControlHeight + verticalSeparatorHeight,
					width, mainControlHeight);
					
				// Skip the separator
				
				// Draw the bottom control box ...
				graphics.drawRect(0, numberControlHeight + 
						(verticalSeparatorHeight * 2) + 
						mainControlHeight, width, numberControlHeight);
			}
			
			
			
			if (_entries != null)
			{
				tempY = numberControlHeight + verticalSeparatorHeight;
				{
				
					var HANDLE_WIDTH:int = 4;
					var HANDLE_VERTICAL_OFFSET:int = 3;
					var handleHeight:int = mainControlHeight + HANDLE_VERTICAL_OFFSET; 
					
					for (var i:int = 0; i < rectangles.length; i++)
					{
						var rectangle:Object = rectangles[i];
						
						if (rectangle.label != null)
						{
							var label:TextField = rectangle.label;
							
							//label.text = "" + rectangle.entry.time;
							label.x = rectangle.x + HANDLE_WIDTH + 2;
						}
						
						graphics.lineStyle(0, 0, 0);
						
						var eventColor:int = getColorForEntry(rectangle.entry);
						if (eventColor != -1)
						{
							graphics.beginFill(eventColor);
							graphics.drawRect(rectangle.x, tempY, rectangle.width, mainControlHeight);
							graphics.endFill();
						}
						
						
						graphics.beginFill(_color);
						graphics.drawRoundRect(rectangle.x, 
							tempY - (HANDLE_VERTICAL_OFFSET/2), HANDLE_WIDTH,
							handleHeight, 2, 2);
						graphics.endFill();
						
						var colors:Array = [ 0xFFFFFF, 0x000000 ];
						var alphas:Array = [ 0.5, 0.6 ];
						var matrix:Matrix = new Matrix();
						matrix.createGradientBox(HANDLE_WIDTH, handleHeight, 0, rectangle.x, 0);
						
						graphics.lineStyle(0, 0, 0.4, true);
						graphics.beginGradientFill(GradientType.LINEAR, colors, alphas, [0x00, 0xFF], 
						 matrix,SpreadMethod.PAD);
						graphics.drawRoundRect(rectangle.x, 
							tempY - (HANDLE_VERTICAL_OFFSET/2), HANDLE_WIDTH,
							handleHeight, 2, 2);
						graphics.endFill();
						
						// Now draw the shadow of the handle on the box
						graphics.beginFill(0x000000, 0.4);
						graphics.drawRect(rectangle.x + HANDLE_WIDTH, tempY, 1, 
							mainControlHeight);
						graphics.endFill();
						
						// Finally, draw the beveled edge
						
						// Bottom bevel
						graphics.lineStyle(1, 0x000000, 0.2);
						graphics.moveTo(rectangle.x + HANDLE_WIDTH,
							tempY + mainControlHeight);
						graphics.lineTo(rectangle.x + rectangle.width,
							tempY + mainControlHeight);
						// Top bevel
						graphics.lineStyle(1, 0xffffff, 0.2);
						graphics.moveTo(rectangle.x + HANDLE_WIDTH, tempY);
						graphics.lineTo(rectangle.x + rectangle.width, tempY);

						if (_selectedIndex == i)
						{
							graphics.lineStyle(0, 0, 0);
							graphics.beginFill(0xFFFFFF, 0.5);
							graphics.drawRect(rectangle.x + (HANDLE_WIDTH/2)-1,
								tempY + (mainControlHeight/2)-5, 2, 5);
							graphics.endFill();
						}
						
						/*
						graphics.lineStyle(1, 0x00FF00, 1, true);
						graphics.beginFill(0xFFFFFF, 0.10);
						graphics.drawRect(rectangle.x, rectangle.y + 20, rectangle.width-5, height - 2);
						graphics.endFill();
						*/
						// Draw the selection
						// Do not draw selection for now 
						/*
						if (_selectedIndex == i)
						{
							// draw triangle for selection on top
							graphics.moveTo(rectangle.x - 3.0, numberControlHeight);
							//graphics.beginFill(0x000000);
							graphics.lineTo(rectangle.x + 3.0, numberControlHeight);
							graphics.lineTo(rectangle.x, numberControlHeight + verticalSeparatorHeight);
							graphics.lineTo(rectangle.x - 3.0, numberControlHeight);
							graphics.endFill();
							
							// draw triangle for selection on bottom
							graphics.beginFill(0x000000);
							graphics.moveTo(rectangle.x - 3, tempY + mainControlHeight + verticalSeparatorHeight);
							graphics.lineTo(rectangle.x, tempY + mainControlHeight);
							graphics.lineTo(rectangle.x + 3, tempY + mainControlHeight + verticalSeparatorHeight);
							graphics.lineTo(rectangle.x - 3, tempY + mainControlHeight + verticalSeparatorHeight);
							graphics.endFill();
						}
						*/ 
					}					
				}
			}
			
			/*
			graphics.lineStyle(1, 0xFF0000, 1, true);
			graphics.beginFill(0, 0);
			graphics.drawRect(0, 0, unscaledWidth, unscaledHeight);
			graphics.endFill();
			*/
		}
		
		private function getColorForEntry(entry:DailyEntry):int
		{
			if (_metaData == null)
			{
				return -1;
			}
			
			var i:int = 0;
			for each (var meta:EventMetaData in _metaData)
			{
				if (meta.value == entry.value)
				{
					// If the entry in the meta data is the first entry then it is always clear
					if (i == 0)
					{
						return -1;
					}
					
					return meta.color;
				}
				
				i++;
			}
			
			return -1;
		}
		
		private function detachEntriesListeners(value:ArrayCollection):void
		{
			if (value == null)
			{
				return;
			}
			
			value.removeEventListener(CollectionEvent.COLLECTION_CHANGE, handleEntriesChange);
		}
		
		private function attachEntriesListeners(value:ArrayCollection):void
		{
			if (value == null)
			{
				return;
			}
			
			value.addEventListener(CollectionEvent.COLLECTION_CHANGE, handleEntriesChange);
		}

		private function handleEntriesChange(event:CollectionEvent):void
		{
			if (event.kind == CollectionEventKind.UPDATE)
			{
				individualEntriesChanged = true;	
 			}
 			else
 			{
 				if (event.kind == CollectionEventKind.REMOVE)
 				{
 					
 					for each (var entry:DailyEntry in event.items)
 					{
 						if (entry == _selectedEntry)
 						{
 							selectedEntry = null;
 						}
 					}
 				}
 				entriesChanged = true;
 			}
 			
 			updateEntryLabelSizes();
			invalidateProperties();
			invalidateDisplayList();
		}
		
		/**
		 * Detects the mouse over an entry (a rectangle) or over the start of
		 * an event, or over the current selection controller
		 */
		private function handleMouseMove(event:MouseEvent):void
		{
			if (!selectable)
			{
				return;
			}
			
			var tempY:int = numberControlHeight + verticalSeparatorHeight;
			
			// If the mouse is down, and we're not dragging, then start dragging
			if (event.buttonDown && selectionRectangle != null)
			{
				if (!editable)
				{
					return;
				}

				if (!dragging)
				{
					// Dispatch beginning event and test for cancel
					var newEvent:WeekdayTimeValueEditorEvent = new WeekdayTimeValueEditorEvent(WeekdayTimeValueEditorEvent.ITEM_EDIT_BEGINNING, false, true);
					
					if (!dispatchEvent(newEvent))
					{
						return;
					}
					
					newEvent = new WeekdayTimeValueEditorEvent(WeekdayTimeValueEditorEvent.ITEM_EDIT_BEGIN);
					dispatchEvent(newEvent);
					
					dragging = true;
					return;
				}
				
				var mouseX:int = Math.floor(event.localX);
				
				// If dragging and the button is down move in increments of 15 minutes
				if (event.shiftKey)
				{
					var minuteEntryTime:int = (Math.floor(Math.floor(mouseX) / pixelToMinuteRatio) / 15);
					var tempInt:int = minuteEntryTime * 15;
					mouseX = tempInt * pixelToMinuteRatio;
					// TODO This is not solving the problem correctly because 
					// when it converts back from pixels it does not yield the
					// correct time. You get times like: 12:28, or 1:14
				}
				
				if (mouseX == selectionRectangle.x)
				{
					return;
				}
				
				// get the previous and next rectangles
				var maxPixel:int = width;
				
				if (_selectedIndex+1 < rectangles.length)
				{
					maxPixel = rectangles[_selectedIndex+1].x;
				}
				
				var minPixel:int = 0;
				var leftRect:Object; // cache these on selection
				
				if (_selectedIndex-1 >= 0)
				{
					leftRect = rectangles[_selectedIndex-1];
					minPixel = leftRect.x + minTimeInPixels;
					
				}
				
				// Limit for now
				if (mouseX < maxPixel-minTimeInPixels && mouseX >= minPixel)
				{
					selectionRectangle.x = mouseX;
					// update width as well
					selectionRectangle.width = maxPixel - selectionRectangle.x;
					// Update numbers for entry
					selectionRectangle.entry.time =  Math.floor(selectionRectangle.x / pixelToMinuteRatio) * 60;
					// update the previous entry if not null
					if (leftRect != null)
					{
						leftRect.width = selectionRectangle.x - leftRect.x;
					}
					 
					invalidateDisplayList(); 
				}

				updateEntryLabelSizes();
				dispatchEvent(new Event(Event.CHANGE));
				return;
			}
			
			
			if (event.localY < tempY)
			{
				return;
			}
			
			tempY = numberControlHeight + (verticalSeparatorHeight * 2) + mainControlHeight;
			if (event.localY > tempY)
			{
				return;
			}
			
			var errorBox:int = 5;
			
			currentRectangle = null;
			selectionRectangle = null;
			
			for (var i:int = 0; i < rectangles.length; i++)
			{
				var rectangle:Object = rectangles[i];
				
				// Calculate if we're over the start of the rectangle
				if (rectangle.x - errorBox <= event.localX && rectangle.x + errorBox > event.localX)
				{
					//trace("Over selection for this: " + rectangle.entry);
					selectionRectangle = rectangle;
					currentRectangle = rectangle;		
					break;
				} 
				
				if (rectangle.x <= event.localX && rectangle.x + rectangle.width >= event.localX)
				{
					//trace("Current over: " + rectangle.entry);
					currentRectangle = rectangle;
					break;
				}
			}
			
			showResizeCursor(selectionRectangle != null);
		}
		
		private function showResizeCursor(value:Boolean):void
		{
			if (value)
			{
				if (cursorID == 0)
				{
					cursorID = CursorManager.setCursor(HORIZONTAL_RESIZE_CURSOR, 2, -7, -4); 
				}
			}
			else
			{
				if (cursorID != 0)
				{
					CursorManager.removeCursor(cursorID);
					cursorID = 0;
				}
			}
		}
		
		
		private function handleMouseDown(event:MouseEvent):void
		{
			if ( !editable )	return;
			if (selectionRectangle == null)
			{
				return;
			}

			selectedEntry = selectionRectangle.entry;
			
			updateSelectedLabel();
			
			dispatchEvent(new Event(Event.CHANGE));
		}
		
		
		private function updateEntryLabelSizes():void
		{
			for each (var rect:Object in rectangles)
			{
				var bestSize:int = rect.label.textWidth + (UITextField.mx_internal::TEXT_WIDTH_PADDING*2);
				if (rect.label != null)
				{
					if (bestSize > rect.width)
					{
						rect.label.width = rect.width - 10;
					}
					else if (rect.width > bestSize && bestSize > rect.label.width)
					{
							rect.label.width = bestSize;
					}
				}
			}
		}
		
		private function updateSelectedLabel():void
		{
			// NOTE MOVE THIS TO DAILY ENTRY OUTPUT
			
			/*
			selectedTimeLabel.text = DailyEntry.timeStringInHoursMinutes(selectionRectangle.entry);
			selectedTimeLabel.setActualSize(
				selectedTimeLabel.getExplicitOrMeasuredWidth(),
				selectedTimeLabel.getExplicitOrMeasuredHeight());
				
			//= selectedTimeLabel.textWidth;
			var tempX:int = selectionRectangle.x - (selectedTimeLabel.getExplicitOrMeasuredWidth()/2);
			
			if (tempX < 0)
			{
				tempX = 0;
			}
			else
			if (tempX + selectedTimeLabel.textWidth >= width)
			{
				tempX = width - selectedTimeLabel.getExplicitOrMeasuredWidth();
			}
			
			//selectedTimeLabel.x = tempX;
			selectedTimeLabel.move(tempX, 0);
			*/
		}
		
		private function handleMouseUp(event:MouseEvent):void
		{
			handleStopDragging();
		}
		
		private var oldEntryTime:int = -1;
		
		private function handleStopDragging():void
		{
			if (dragging && selectionRectangle != null)
			{
				var event:WeekdayTimeValueEditorEvent = new WeekdayTimeValueEditorEvent(WeekdayTimeValueEditorEvent.ITEM_EDIT_END)
				dispatchEvent(event);
				
			}
			
			showResizeCursor(false);
			
			dragging = false;
		}
		
		public function pixelToMinutes(x:int):int
		{
			if (x < 0 || x > width)
			{
				return 0;
			}
			
			return x / pixelToMinuteRatio;
		}
		
		private function handleRollOut(event:MouseEvent):void
		{
			handleStopDragging();
		}
	}
}
