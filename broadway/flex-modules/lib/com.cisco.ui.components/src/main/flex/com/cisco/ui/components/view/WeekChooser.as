package com.cisco.ui.components.view
{
	import com.cisco.ui.components.view.renderer.CheckBoxImageItemRenderer;
	
	import flash.events.Event;
	
	import mx.controls.List;
	import mx.controls.PopUpButton;
	import mx.core.ClassFactory;
	import mx.core.EventPriority;
	import mx.core.IFactory;
	import mx.events.ListEvent;

	public class WeekChooser extends PopUpButton
	{
		private var weekDropDown:List;
		private var _selectedWeekDays:Array;
		
		[Embed(source="assets/week.gif")]
		public var weekIcon:Class;
		
		public static const WEEK_NAMES:Array = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
		
		public function WeekChooser()
		{
			super();
			weekDropDown = new List();
			weekDropDown.itemRenderer = checkBoxRenderer;
			weekDropDown.dataProvider = WEEK_NAMES;
			popUp = weekDropDown;
			setStyle("icon",weekIcon);
			labelPlacement = "right";
			openAlways = true;
            popUp.addEventListener(ListEvent.ITEM_CLICK, popUpItemClickHandler,false,EventPriority.BINDING);
		}
		
		public function get selectedWeekDays():Array {
			return _selectedWeekDays;
		}
		
		public function set selectedWeekDays(value:Array):void {
			this._selectedWeekDays = value;
			invalidateProperties();
		}
		
		public function get selectedWeekNames():String {
			if (selectedWeekDays == null )	return "";
			return selectedWeekDays.toString();
		}
		
		public function set selectedWeekNames(value:String):void {
			if ( value == null ) {
				selectedWeekDays = null;
			} else {
				selectedWeekDays = value.split(",");
			}
		}
		
		protected function get checkBoxRenderer():IFactory {
			var factory:ClassFactory = new ClassFactory(CheckBoxImageItemRenderer);
			factory.properties = { selectedFunction: isWeekSelected, changeHandler: weekSelected};
			return factory;
		}
		
		protected function popUpItemClickHandler(event:Event):void {
			event.stopImmediatePropagation();
			event.stopPropagation();
			event.preventDefault();
		}
		
		protected function isWeekSelected(weekName:String):Boolean {
			if ( selectedWeekDays != null ) {
				return selectedWeekDays.indexOf(weekName) != -1;
			}
			return false;
		}
		
		protected function weekSelected(weekName:String,selected:Boolean):void {
			if ( selectedWeekDays == null && !selected )	return;
			if ( selectedWeekDays == null ) {
				selectedWeekDays = new  Array();
			}
			
			var anIndex:int = selectedWeekDays.indexOf(weekName);
			if ( anIndex == -1 && selected ) {
				selectedWeekDays.push(weekName);
			} else if ( anIndex != -1 && !selected ) {
				selectedWeekDays.splice(anIndex,1);
			}
		}
		
		
	}
}