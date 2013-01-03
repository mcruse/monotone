package com.cisco.ui.components.view.renderer
{
	import flash.events.Event;
	import flash.events.MouseEvent;
	
	import mx.controls.CheckBox;
	import mx.controls.LinkButton;
	import mx.controls.listClasses.BaseListData;
	import mx.controls.listClasses.IDropInListItemRenderer;
	import mx.controls.listClasses.IListItemRenderer;
	import mx.core.UIComponent;

	public class CheckBoxImageItemRenderer extends UIComponent implements IListItemRenderer,IDropInListItemRenderer
	{
		private var imageField:LinkButton;
		private var _tooltipMessage:String;
		
		private var _icon:Class;
		protected var iconChangeFlag:Boolean;
		protected var toolTipChangeFlag:Boolean;
		
		public var imageClickHandler:Function;
		
		public var imageVisibleFunction:Function;
		
		public var selectedFunction:Function;
		public var changeHandler:Function;
		private var dataChangeFlag:Boolean;
		private var checkBox:CheckBox;
		private var _listData:BaseListData;
		private var listDataChangeFlag:Boolean;
		private var _data:Object;
		public var checkBoxVisibleFunction:Function;
		
		
		public function get tooltipMessage():String {
			return _tooltipMessage;
		}
		
		public function set tooltipMessage(value:String):void {
			if ( _tooltipMessage != value ) {
				_tooltipMessage = value;
				toolTipChangeFlag = true;
				invalidateProperties();
				invalidateDisplayList();
			}
		}
		
		public function get icon():Class {
			return _icon;
		}
		
		public function set icon(value:Class):void {
			if ( _icon != value ) {
				_icon = value;
				iconChangeFlag = true;
				invalidateProperties();
				invalidateDisplayList();
			}
		}
		
		override protected function createChildren():void {
			super.createChildren();
			
			if ( checkBox == null ) {
				checkBox = new CheckBox();
				checkBox.addEventListener(Event.CHANGE,_changeHandler);
				addChild(checkBox);
			}
			
			if ( imageField == null ) {
				imageField = new LinkButton();
				imageField.addEventListener(MouseEvent.MOUSE_DOWN, onMouseClick);
				addChild(imageField);
			}
		}
		
		private function _changeHandler(event:Event):void {
			event.stopImmediatePropagation();
			event.stopPropagation();
			event.preventDefault();
			if ( changeHandler != null ) {
				changeHandler(data,checkBox.selected);
			}
		}
		
		protected function onMouseClick(event:Event):void {
			event.stopImmediatePropagation();
			event.stopPropagation();
			event.preventDefault();
			
			if ( imageClickHandler != null ) {
				imageClickHandler(data);
			}
		}
		
		public function get data():Object {
			return _data;
		}

		public function set data(value:Object):void {
			_data = value;
			dataChangeFlag = true;
			invalidateProperties();
		}
		
		public function get listData():BaseListData {
			return _listData;
		}
		
		public function set listData(value:BaseListData):void {
			_listData = value;
			listDataChangeFlag = true;
			invalidateProperties();
		}
		
		

		override protected function commitProperties():void {
			

			if ( dataChangeFlag ) {
				checkBox.enabled = true;
				if ( checkBoxVisibleFunction != null && checkBox != null ) {
					checkBox.enabled = checkBoxVisibleFunction(data);
				}
				if ( checkBox.enabled && selectedFunction != null && checkBox != null ) {
					checkBox.selected = selectedFunction(data);
				} else {
					checkBox.selected = false;
				}
				
				if ( imageVisibleFunction != null && imageField != null ) {
					imageField.visible = imageVisibleFunction(data);
				} else {
					imageField.visible = false;
				}
				dataChangeFlag = false;
			}
			
			if ( listDataChangeFlag ) {
				listDataChangeFlag = false;
				if ( checkBox != null && listData != null )
					checkBox.label = listData.label;
			}
			
			if ( iconChangeFlag ) {
				iconChangeFlag = false;
				imageField.setStyle("icon",icon);
				imageField.toolTip = tooltipMessage;
			}
			
			if ( toolTipChangeFlag ) {
				toolTipChangeFlag = false;
				imageField.toolTip = tooltipMessage;
			}
			
			super.commitProperties();
		}
		
		override protected function updateDisplayList(unscaledWidth:Number, unscaledHeight:Number):void {
			super.updateDisplayList(unscaledWidth,unscaledHeight);
			
			imageField.move(unscaledWidth - imageField.measuredWidth - 1, 1);
			imageField.setActualSize(imageField.measuredWidth,imageField.measuredHeight);
			
			checkBox.move(1,0);
			checkBox.setActualSize(checkBox.measuredWidth,checkBox.measuredHeight);
		}
		
	}
}