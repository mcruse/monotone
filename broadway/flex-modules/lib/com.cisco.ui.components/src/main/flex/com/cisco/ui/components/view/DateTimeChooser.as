package com.cisco.ui.components.view
{
	import flash.events.Event;
	
	import mx.controls.DateChooser;
	import mx.controls.NumericStepper;
	import mx.core.UITextField;
	import mx.core.mx_internal;
	import mx.events.CalendarLayoutChangeEvent;
	import mx.events.NumericStepperEvent;
	import mx.formatters.DateFormatter;
	
	use namespace mx_internal;

	public class DateTimeChooser extends DateChooser
	{
		private var hourField:NumericStepper;
		private var minuteField:NumericStepper;
		private var selectedDateChanged:Boolean;
		private var formatter:DateFormatter = new DateFormatter();
		
		private var _timeNavigationEnabled:Boolean = true;
		
		public function DateTimeChooser() {
			super();
			addEventListener(CalendarLayoutChangeEvent.CHANGE,calendarLayoutChangeHandler,false,100);
		}
		
		public function calendarLayoutChangeHandler(event:CalendarLayoutChangeEvent):void {
			super.selectedDate = event.newDate;
			timeChangeHandler();
		}
		
		
		override protected function createChildren():void {
			super.createChildren();
			
			if ( _timeNavigationEnabled )
				createTimeFields();
			
		}
		
		protected function createTimeFields():void {
			if ( hourField == null ) {
				hourField = new NumericStepper();
				hourField.minimum = 0;
				hourField.maximum = 23;
				hourField.stepSize = 1;
				hourField.maxChars = 2;
				hourField.addEventListener(NumericStepperEvent.CHANGE,timeChangeHandler);
				addChild(hourField);
			}
			if ( minuteField == null ) {
				minuteField = new NumericStepper();
				minuteField.minimum = 0;
				minuteField.maximum = 59;
				minuteField.stepSize = 1;
				minuteField.maxChars = 2;
				minuteField.addEventListener(NumericStepperEvent.CHANGE,timeChangeHandler);
				addChild(minuteField);
			}
		}
		
		private function mouseHandler(event:Event):void {
			event.stopImmediatePropagation();
			event.preventDefault();
		}
		
		protected function timeChangeHandler(event:Event=null):void {
			var date:Date = this.selectedDate;
			date.setHours(hourField.value,minuteField.value,0,0);
		}
		
		override mx_internal function scrubTimeValue(value:Object):Object {
			if ( value is Date )
				return value;
			return super.scrubTimeValue(value);
		}
		
		override public function set selectedDate(value:Date):void {
			//if ( super.selectedDate != value ) {
				super.selectedDate = value;
				selectedDateChanged = true;
				invalidateProperties();
				invalidateDisplayList();
			//}
		}
		
		override protected function commitProperties():void {
			super.commitProperties();
			
			if ( selectedDateChanged ) {
				selectedDateChanged = false;
				if ( selectedDate != null ) {
					
					if ( hourField ) {
						formatter.formatString = "JJ";
						hourField.value = Number(formatter.format(selectedDate));
					}
					
					if ( minuteField ) {
						formatter.formatString = "NN";
						minuteField.value = Number(formatter.format(selectedDate));
					}
				}
			}
						
		}
		
		override protected function updateDisplayList(unscaledWidth:Number, unscaledHeight:Number):void {
			super.updateDisplayList(unscaledWidth,unscaledHeight);
			
			hourField.move(backMonthButton.x +backMonthButton.width + 2,backMonthButton.y);
			hourField.setActualSize(40,hourField.measuredHeight);
			minuteField.move(hourField.x + hourField.width + 2,backMonthButton.y);
			minuteField.setActualSize(40,minuteField.measuredHeight);
			monthDisplay.x = minuteField.x + 7;
			(monthDisplay as UITextField).setStyle("textAlign","center");
		}
		
		override protected function measure():void {
			super.measure();
			
			measuredWidth += 80;
			measuredMinWidth += 80;
		}
		
		
		
	}
}