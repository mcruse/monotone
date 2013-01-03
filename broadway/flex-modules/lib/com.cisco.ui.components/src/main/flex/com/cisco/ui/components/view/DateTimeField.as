package com.cisco.ui.components.view
{
	import mx.controls.PopUpButton;
	import mx.events.CalendarLayoutChangeEvent;
	import mx.formatters.DateFormatter;
	
	/**
	 *  Dispatched when a date is selected or changed,
	 *  and the DateChooser control closes.
	 *
	 *  @eventType mx.events.CalendarLayoutChangeEvent.CHANGE
	 */
	[Event(name="change", type="mx.events.CalendarLayoutChangeEvent")]

	public class DateTimeField extends PopUpButton
	{
		private var _selectedDate:Date = new Date();
		private var selectedDateChanged:Boolean;
		private var dateFormatter:DateFormatter = new DateFormatter();
		private var dateChooser:DateTimeChooser;
		public var labelFunction:Function;
		public var yearNavigationEnabled:Boolean;
		public var parseFunction:Function;
		public var showToday:Boolean=true;
		
		[Embed(source="assets/calendar.jpg")]
		public var calendarIcon:Class;
		
		public function DateTimeField()
		{
			super();
			dateChooser = new DateTimeChooser();
			dateChooser.addEventListener(CalendarLayoutChangeEvent.CHANGE,calendarLayoutChangeHandler);
			popUp = dateChooser;
			minWidth = 100;
			dateFormatter.format("DD/MM/YY JJ:NN");
			setStyle("icon",calendarIcon);
			labelPlacement = "right";
			openAlways = true;
			showToday = true;
			setStyle("fontSize",10);
			yearNavigationEnabled = true;
		}
		
		protected function calendarLayoutChangeHandler(event:CalendarLayoutChangeEvent):void {
			this.close();
			selectedDate = dateChooser.selectedDate;
			updateDateLabel();
			dispatchEvent(event);
		}
		
		public function get selectedDate():Date {
			return _selectedDate;
		}
		
		public function set selectedDate(value:Date):void {
			//if ( _selectedDate != value ) {
				_selectedDate = value;
				selectedDateChanged = true;
				invalidateProperties();
				invalidateDisplayList();
			//}
		}
		
		protected function updateDateLabel():void {
			if ( labelFunction != null )
				label = labelFunction(selectedDate) as String;
			else
				label = dateFormatter.format(selectedDate);
		}
		
		override protected function commitProperties():void {
			super.commitProperties();
			
			if ( selectedDateChanged ) {
				selectedDateChanged = false;
				
				if ( selectedDate != null ) {
					updateDateLabel();
					dateChooser.selectedDate = selectedDate;
					invalidateSize();
					measuredWidth = this.textField.measuredWidth;
				}
				
			}
			dateChooser.yearNavigationEnabled = yearNavigationEnabled;
		}
		
	}
}