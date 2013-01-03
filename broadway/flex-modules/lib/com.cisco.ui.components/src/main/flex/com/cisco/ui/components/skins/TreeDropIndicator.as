package com.cisco.ui.components.skins
{
	import flash.display.Graphics;
	
	import mx.skins.ProgrammaticSkin;

	public class TreeDropIndicator extends ProgrammaticSkin
	{
		public function TreeDropIndicator()
		{
			super();
		}
		
		override protected function updateDisplayList(unscaledWidth:Number, unscaledHeight:Number):void {
			super.updateDisplayList(unscaledWidth, unscaledHeight);
			
			var g:Graphics = graphics;
			
			g.clear();
			g.beginFill(0xa1bde2, 0.5);
			g.drawRect(-5, -1, unscaledWidth, 23);
		}
	}
}