package com.cisco.ui.components.view
{

	import flash.display.Sprite;

	import mx.controls.Alert;
	import mx.core.Application;
	import mx.events.CloseEvent;

	public class NbmAlert extends Alert
	{
		public static const CONFIRMATION:int = 0;
		public static const INFORMATION:int = 1;
		public static const ERROR:int = 2;
		public static const WARNING:int = 3;
		
		[Embed(source="assets/warning.png")]
		public static const WARNING_ICON:Class;

		[Embed(source="assets/information.png")]
		public static const INFORMATION_ICON:Class;

		[Embed(source="assets/error.png")]
		public static const ERROR_ICON:Class;
			
		public static function show(msgTxt:String, alertType:int=INFORMATION,
					title:String = null, closeHandler:Function=null):Alert
		{
			var iconClass:Class = getIcon(alertType);
			if (title == null)
				title = getTitle(alertType);

			var buttons:uint = OK;
			var defButton:uint = OK;
			if (alertType == CONFIRMATION)
			{
				buttons = YES|NO;
				defButton = NO;
			}

			var alert:Alert = Alert.show(msgTxt, title, buttons,
				Sprite(Application.application), closeHandler != null ? closeHandler : defCloseHandler, null, defButton);
			alert.minHeight = 120;
			alert.minWidth = 300;
			alert.titleIcon = iconClass;
			alert.invalidateDisplayList();
			return alert;
		}

	    private	static function defCloseHandler(event:CloseEvent):void
		{
        	Application.application.resetFocus();
        }

		private static function getIcon(alertType:int):Class
		{
			switch(alertType)
			{
				case CONFIRMATION:
				case WARNING:
					return WARNING_ICON;
				case ERROR:
					return ERROR_ICON;
				default:
					return INFORMATION_ICON;
			}
		}

		private static function getTitle(alertType:int):String
		{
			switch(alertType)
			{
				case CONFIRMATION:
					return "Confirmation";
				case WARNING:
					return "Warning";
				case ERROR:
					return "Error";
				default:
					return "Message";
			}
		}

	}
}
