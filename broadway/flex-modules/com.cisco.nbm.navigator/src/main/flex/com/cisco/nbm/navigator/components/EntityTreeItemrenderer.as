/*************************************************
 * Copyright (c) 2010 by Cisco Systems, Inc.
 * All Rights Reserved.
 * Author: prthoma@cisco.com
 *
 * Description: EntityTreeItemrenderer is a AdvancedDataGridGroupItemRenderer which is used
 * to show the offline status of the node in a ADG(CiscoTree)
 *************************************************/
package com.cisco.nbm.navigator.components
{
	import com.cisco.nbm.entities.EntityStatus;

	import flash.display.Sprite;
	import flash.geom.ColorTransform;
	import flash.xml.*;

	import mx.collections.*;
	import mx.controls.Image;
	import mx.controls.advancedDataGridClasses.AdvancedDataGridGroupItemRenderer;
	import mx.controls.listClasses.*;
	import mx.core.mx_internal;
	use namespace mx_internal;

	public class EntityTreeItemrenderer extends AdvancedDataGridGroupItemRenderer {
		private var circle:Sprite = new Sprite();

		public var onlineColor:int = 0x000000;

		public var onlineFontStyle:String = 'normal';

		public var offlineColor:int = 0x999999;

		public var offlineFontStyle:String = 'italic';

		public var onlineIconColor:int = 0x00CC00;

		public var networkOfflineIconColor:int = 0xFF0000;

		public var linkOfflineIconColor:int = 0xFF9900;

		public var frameworkOfflineIconColor:int = 0xFFCC00;

		// Icon overlay
		[Embed(source="assets/TreeIcons/icon_overlay.png")]
		private var iconOverlayImage:Class;

        protected var icon_overlay:Image;
		private var OFFLINE:Boolean = false;
		private var LINK_OFF:Boolean = false;

		public function EntityTreeItemrenderer()
		{
			super();
		}


		/**
		 * Add an icon(image) to cell stage
		 *
		 */
		override protected function createChildren():void
		{
			super.createChildren();

			// Add COLOR sprite
			circle.graphics.beginFill(0xFFFFFF);
         	circle.graphics.drawCircle(4, 4, 4);
         	circle.graphics.endFill();
         	addChild(circle);


         	// Add icon image
			icon_overlay = new Image();
	    	icon_overlay.source = iconOverlayImage;
			icon_overlay.setStyle( "verticalAlign", "middle" );
			addChild(icon_overlay);
	    }

	    /**
	     * Overrides data()
	     * Sets and resets font style/color depending on status
	     * @param value Value Object of the rendering item
	     *
	     */
	    override public function set data(value:Object):void
		{
			if(value != null){
				super.data = value;

				// Check status
				if(value.status == EntityStatus.NETWORK_OFF)
				{
					OFFLINE = true;
					setColorTo(networkOfflineIconColor);
				} else if(value.status == EntityStatus.FRAMEWORK_OFF) {
					OFFLINE = true;
					setColorTo(frameworkOfflineIconColor);
				}
				else if(value.status == EntityStatus.LINK_OFF) {
					LINK_OFF = true;
					setColorTo(linkOfflineIconColor);
				}
				else {
					OFFLINE = false;
					setColorTo(onlineIconColor);
				}

				// Change font color and style
				if(OFFLINE)
				{
					setStyle("color", offlineColor);
				    setStyle("fontStyle", offlineFontStyle);
				}
				else if(LINK_OFF)
				{
					setStyle("color", offlineColor);
				    setStyle("fontStyle", onlineFontStyle);
				}
				else {
					setStyle("color", onlineColor);
				    setStyle("fontStyle", onlineFontStyle);
				}
			}
	    }

	    /**
	     * overrides updateDisplayList()
	     * Used to set and reset the offline icon visibility and relative changes on
	     * folder icon and label text
	     *
	     * @param unscaledWidth Cell Width
	     * @param unscaledHeight Cell Height
	     *
	     */
	    override protected function updateDisplayList(unscaledWidth:Number, unscaledHeight:Number):void
		{

			super.updateDisplayList(unscaledWidth, unscaledHeight);

	        if(super.data)
	        {
	        	if (super.icon != null)
		   		{
		   			// Reposition the icons
		   			repositionIcons();
			    }
			}
		}

		// Change the color of the icon sprite
		private function setColorTo(newColor:int):void{
			var colorTransform:ColorTransform = circle.transform.colorTransform;
			colorTransform.color = newColor;
			circle.transform.colorTransform = colorTransform;
		}

		// Reposition the icons
		private function repositionIcons():void{
			icon_overlay.width = 8;
			icon_overlay.height = 8;
			icon_overlay.x = super.icon.x;
		    super.icon.x = icon_overlay.x + 10;
		    icon_overlay.y = (unscaledHeight - icon_overlay.height) / 2 - 1;
		    if (icon.x + icon.width > unscaledWidth)
		    	icon.setActualSize(0, unscaledHeight);
		    super.label.x = super.icon.x + super.icon.width + 3;
		    super.label.setActualSize(Math.max(unscaledWidth - super.label.x, 4), unscaledHeight);
		    //
		    circle.x = icon_overlay.x;
		    circle.y = icon_overlay.y;
		}

	}
}