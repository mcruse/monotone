package com.cisco.ui.components.view
{
	import com.cisco.ui.components.event.UIDataEvent;
	import com.cisco.ui.components.vo.IDraggable;
	
	import flash.events.Event;
	import flash.events.KeyboardEvent;
	import flash.events.MouseEvent;
	import flash.geom.Point;
	import flash.ui.Keyboard;
	
	import mx.containers.HBox;
	import mx.containers.ViewStack;
	import mx.controls.Button;
	import mx.controls.Label;
	import mx.controls.LinkBar;
	import mx.controls.Spacer;
	import mx.core.EventPriority;
	import mx.core.mx_internal;
	import mx.managers.PopUpManager;
	import mx.styles.StyleProxy;
	use namespace mx_internal;
	
	/**
	 *  Dispatched when the Finish clicked.
	 *  @eventType com.cisco.nbmm.security.view.controls.Wizard.FINISH
	 */
	[Event(name="finish", type="flash.events.Event")]

	public class Wizard extends ViewStack implements IDraggable
	{
		protected var tabBar:LinkBar;
		public var tabWidth:Number = 150;
		private var previousButton:Button;
		private var nextButton:Button;
		private var bottomContainer:HBox;
		private var header:Header;
		private var titleLabel:Label;
		public var _title:String;
		private var titleChangeFlag:Boolean;
		private var isDragging:Boolean=false;
		private var isResizing:Boolean=false;
		private var resizeOffset:Number = 5;
		private var resizingCorner:String;
		private var resizeHandle:ResizeHandler;
		private var closeButton:Button;
		public var showCloseButton:Boolean;
		
		public static const FINISH:String = "finish";
		
		private static var _closeButtonStyleFilters:Object = 
	    {
	        "closeButtonUpSkin" : "closeButtonUpSkin", 
	        "closeButtonOverSkin" : "closeButtonOverSkin",
	        "closeButtonDownSkin" : "closeButtonDownSkin",
	        "closeButtonDisabledSkin" : "closeButtonDisabledSkin",
	        "closeButtonSkin" : "closeButtonSkin",
	        "repeatDelay" : "repeatDelay",
	        "repeatInterval" : "repeatInterval"
	    };
		
		public function Wizard()
		{
			super();
			setStyle("borderStyle","outset");
			setStyle("backgroundColor",0xffffff);
			addEventListener(FINISH,finishHandler,false,EventPriority.DEFAULT_HANDLER);
		}
		
		public function get title():String {
			return _title;
		}
		
		public function set title(value:String):void {
			_title = value;
			titleChangeFlag = true;
			invalidateProperties();
		}
		
		override protected function createChildren():void {
			super.createChildren();
			
			if ( tabBar == null ) {
				tabBar = new LinkBar();
				tabBar.setStyle("borderStyle","solid");
				tabBar.direction = "vertical";
				rawChildren.addChild(tabBar);
			}
			
			if ( header == null ) {
				header = new Header();
				header.direction = "horizontal";
				header.setStyle("borderStyle","solid");
				header.setStyle("verticalAlign","middle");
				header.setStyle("paddingRight",5);
				rawChildren.addChild(header);
			}
			
			if ( titleLabel == null ) {
				titleLabel = new Label();
				titleLabel.setStyle("fontWeight","bold");
				titleLabel.setStyle("fontSize",20);
				header.addChild(titleLabel);
			}
			
			
			
			// Create the closeButton as a child of the titleBar.
			if (closeButton == null )
			{
				closeButton = new Button();
				closeButton.styleName = new StyleProxy(this, _closeButtonStyleFilters);
				
				closeButton.upSkinName = "closeButtonUpSkin";
				closeButton.overSkinName = "closeButtonOverSkin";
				closeButton.downSkinName = "closeButtonDownSkin";
				closeButton.disabledSkinName = "closeButtonDisabledSkin";
				/* closeButton.skinName = "closeButtonSkin"; */
				closeButton.explicitWidth = closeButton.explicitHeight = 16;
				closeButton.width = closeButton.height = 16;
				
//				closeButton.focusEnabled = false;
//				closeButton.visible = false;
				closeButton.enabled = enabled;
				closeButton.label = "Close";
				
				var spacer:Spacer = new Spacer();
				spacer.percentWidth = 100;
				header.addChild(spacer);
				
				closeButton.addEventListener(MouseEvent.CLICK,closeClickHandler);
				
				header.addChild(closeButton);
				closeButton.owner = this;
			}
			
			if ( bottomContainer == null ) {
				bottomContainer = new HBox();
				bottomContainer.setStyle("borderStyle","solid");
				bottomContainer.setStyle("horizontalAlign","right");
				bottomContainer.setStyle("verticalAlign","middle");
				bottomContainer.setStyle("verticalGap",5);
				bottomContainer.setStyle("paddingRight",5);
				rawChildren.addChild(bottomContainer);
			}
			
			if ( previousButton == null ) {
				previousButton = new Button();
				previousButton.label = "Previous";
				previousButton.addEventListener(MouseEvent.CLICK,previousClickHandler);
				bottomContainer.addChild(previousButton);
				
			}

			if ( nextButton == null ) {
				nextButton = new Button();
				nextButton.label = "Next";
				nextButton.addEventListener(MouseEvent.CLICK,nextClickHandler);
				bottomContainer.addChild(nextButton);
			}
			
		}
		
		override protected function commitProperties():void {
			super.commitProperties();
			
			if (tabBar && tabBar.dataProvider != this && numChildren > 0 && getChildAt(0)) {
				tabBar.dataProvider = this;
			}
			
			if ( titleChangeFlag ) {
				titleChangeFlag = false;
				titleLabel.text = title;
			}
			
			if ( selectedIndex == 0 ) {
				previousButton.enabled = false;
			} else {
				previousButton.enabled = true;
			}
			
			if ( selectedIndex == numChildren -1 ) {
				nextButton.label = "Finish";
			} else {
				nextButton.label = "Next";
			}
			
		}
		
		override protected function updateDisplayList(unscaledWidth:Number, unscaledHeight:Number):void {
			super.updateDisplayList(unscaledWidth,unscaledHeight);
			
			header.move(0,0);
			header.setActualSize(unscaledWidth,header.measuredHeight);
			
			bottomContainer.move(0,unscaledHeight - bottomContainer.measuredHeight - 10 );
			bottomContainer.setActualSize(unscaledWidth,bottomContainer.measuredHeight + 10 );
			
			tabBar.move(0, header.y + header.height -1 );
			tabBar.setActualSize(tabWidth,unscaledHeight - header.height - bottomContainer.height + 2);
			
			//closeButton.visible = showCloseButton;
			//closeButton.includeInLayout = showCloseButton;
			
			//closeButton.move(unscaledWidth - 16 - 2, 2);
			closeButton.setActualSize( 16, 16);
		}
		
		override protected function get contentX():Number {
			return super.contentX + tabWidth + 2;
		}
		
		override protected function get contentY():Number {
			return super.contentY + header.measuredHeight + 2;
		}
		
		override protected function get contentWidth():Number {
			return super.contentWidth - tabWidth - 4;
		}
		
		override protected function get contentHeight():Number {
			return super.contentHeight - bottomContainer.measuredHeight - header.measuredHeight - 12;
		}
		
		protected function previousClickHandler(event:MouseEvent):void {
			if ( selectedIndex > 0 )
				selectedIndex--;
		}
		
		protected function nextClickHandler(event:MouseEvent):void {
			if ( selectedIndex < numChildren - 1 ) {
				selectedIndex++;
			} else {
				dispatchEvent(new Event(FINISH));
			}
		}
		
		protected function closeClickHandler(event:MouseEvent):void {
			closeThis();
		}
		
		
		protected function finishHandler(event:Event):void {
			if ( !event.isDefaultPrevented() ) {
				if ( this.isPopUp ) {
					closeThis();
				}
			}
		}
		
		override protected function keyDownHandler(event:KeyboardEvent):void {
			switch(event.keyCode) {
				case Keyboard.ESCAPE :
					closeThis();
					return;
			}
			super.keyDownHandler(event);
		}
		
		protected function closeHandler(event:Event=null):void {
			closeThis();
		}
		
		protected function closeThis(needEvent:Boolean=false):void {
			PopUpManager.removePopUp(this);
			if ( needEvent )
				dispatchEvent(new UIDataEvent(UIDataEvent.CLOSE));
		}
		
		override public function set isPopUp(value:Boolean):void {
			super.isPopUp = value;
			if ( isPopUp ) {
				resizeHandle = new ResizeHandler(this);
			} else {
				if ( resizeHandle ) {
					resizeHandle.component = null;
					resizeHandle = null;
				}
			}
		}
		
		public function isDraggableArea(point:Point):Boolean {
			return point.x >= header.x && point.x <= header.x + header.width && point.y >= header.y && point.y <= header.y + header.height;
		}
		
		
	}
}