package com.cisco.nbm.navigator.components
{
	import flash.display.DisplayObject;
	import flash.text.TextFieldAutoSize;
	import flash.text.TextLineMetrics;

	import mx.controls.Button;
	import mx.styles.StyleManager;

	public class EntityButtonRenderer extends Button
	{
		public function EntityButtonRenderer()
		{
			super();
		}

		override protected function createChildren():void
		{
		// Create a UITextField to display the label.
		if (!textField)
		{
		textField = new NoTruncationUITextField();
		textField.styleName = this;
		addChild(DisplayObject(textField));
		}
		super.createChildren();
		textField.multiline = true;
		textField.wordWrap = true;
		textField.autoSize = TextFieldAutoSize.LEFT;

		}

		override protected function updateDisplayList(unscaledWidth:Number, unscaledHeight:Number):void
		{
		super.updateDisplayList(unscaledWidth, unscaledHeight);
		textField.y = (this.height-textField.height)>>1;
		textField.x = (this.width - textField.width)>>1;

		}

		override protected function measure():void
	  	{
		   if (!isNaN(explicitWidth))
		   {
		    var w:Number = explicitWidth;
		    w -= getStyle("horizontalGap") + getStyle("paddingLeft") + getStyle("paddingRight");
			textField.width = w;
		   }
		   super.measure();

	  	}

     override public function measureText(s:String):TextLineMetrics
	 {
	   textField.text = s;
	   var lineMetrics:TextLineMetrics = textField.getLineMetrics(0);
	   lineMetrics.width = textField.textWidth + textField.text.length;
	   lineMetrics.height = textField.textHeight + 4;
	   return lineMetrics;
	  }



	}
}
	import flash.text.TextFieldAutoSize;

    import mx.core.UITextField;

    class NoTruncationUITextField extends UITextField
    {

        public function NoTruncationUITextField()
        {
            super();
            multiline = true;
            wordWrap = true;
            autoSize = TextFieldAutoSize.LEFT;
        }

        override public function truncateToFit(s:String = null):Boolean
        {
            return false;
        }
    }
