package com.cisco.ui.components
{
	import flash.text.Font;
	
	import mx.collections.ArrayCollection;
	import mx.collections.Sort;
	import mx.collections.SortField;
	import mx.controls.ComboBox;
	import mx.core.ClassFactory;
	import mx.events.FlexEvent;

	public class FontFamilyDropDown extends ComboBox
	{
		[Bindable]
		private var fontList:ArrayCollection;
		
		private var _fontFamily:String;
		
		public function FontFamilyDropDown()
		{
			super();
			
			addEventListener(FlexEvent.CREATION_COMPLETE, handleCreationComplete);
		}
		
		public function set selectedFontFamily(value:String):void {
			if (value == _fontFamily) {
				return;
			}
			
			_fontFamily = value;
			
			if (!initialized) {
				return;
			}
			
			for each (var font:Font in fontList) {
				if (font.fontName == _fontFamily) {
					selectedItem = font;
					break;
				}
			}
		}
		
		public function get selectedFontFamily():String {
			var si:Font = selectedItem as Font;
			
			if (si == null) {
				return null;
			}
			
			return si.fontName;
		}
		
		private function handleCreationComplete(event:FlexEvent):void {
			fontList = new ArrayCollection(Font.enumerateFonts(true));
			labelField = "fontName";
			
			var sort:Sort = new Sort();
			sort.fields = [new SortField("fontName")];
			fontList.sort = sort;
			fontList.refresh();
			
			dataProvider = fontList;
			itemRenderer = new ClassFactory(FontFamilyComboBoxRenderer);
			dropdown.variableRowHeight = true;
			
			if (_fontFamily != null) {
				selectedFontFamily = _fontFamily;
			}
		}
		
	}
}