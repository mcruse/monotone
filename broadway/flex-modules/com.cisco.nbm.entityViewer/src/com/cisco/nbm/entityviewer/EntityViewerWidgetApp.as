package com.cisco.nbm.entityviewer
{
	import com.cisco.nbm.browserbridge.BrowserBridge;
	import com.cisco.nbm.browserbridge.BrowserBridgeEvent;
	import com.cisco.nbm.browserbridge.ui.connection.AuthenticationDialog;
	import com.cisco.nbm.entities.Entity;
	import com.cisco.nbm.entities.EntityEvent;
	import com.cisco.nbm.entities.EntityManager;
	import com.cisco.nbm.entities.EntityPropertyChangeEvent;
	import com.cisco.nbm.xmlrpc.v2.MediatorNode;
	import com.cisco.nbm.xmlrpc.v2.XMLRPCService;
	import com.cisco.nbm.xmlrpc.v2.XMLRPCServiceEvent;
	
	import flash.events.ContextMenuEvent;
	import flash.events.ErrorEvent;
	import flash.events.MouseEvent;
	import flash.ui.ContextMenu;
	import flash.ui.ContextMenuItem;
	
	import mx.controls.Alert;
	import mx.core.Application;
	import mx.events.CloseEvent;
	import mx.events.FlexEvent;
	import mx.logging.ILogger;
	import mx.logging.Log;
	import mx.logging.targets.TraceTarget;
	import mx.utils.StringUtil;

	/**
	 * Base class for widget application functionality.
	 */
	public class EntityViewerWidgetApp extends EntityViewerWidgetAppBase
	{
		protected var logger:ILogger;
		
		public static const FV_TOPIC:String = "topic";
		
		public static const DEFAULT_TOPIC:String = "/topic";
		
		public static const FV_ENTITY:String = "entity"; 
		
		private static const DEFAULT_ENTITY_MANAGER_URI:String = "/services/Entity Manager";
		
		protected var topic:String = DEFAULT_TOPIC; 
		
		private var initialEnitty:String;
		
		[Bindable]
		protected var entity:Entity;
		
		protected var entityManager:EntityManager;
		
		protected var service:XMLRPCService;
		
		protected var browserBridge:BrowserBridge;
		
		[Bindable]
		protected var embedded:Boolean = false;
			
		protected var initialSelectedEntity:String;

		[Bindable]
		protected var connected:Boolean = false; 	
		
		[Bindable]
		protected var ready:Boolean =false;	
		
		protected var entityManagerURI:String = DEFAULT_ENTITY_MANAGER_URI;
		
		protected var debug:Boolean = true;
		
		public function EntityViewerWidgetApp()
		{
			super();
						
			addEventListener(FlexEvent.CREATION_COMPLETE, handleCreationComplete);
		}
		
		/**
		 * Override to provide own functionality
		 */
		protected function init():void
		{
			
		}
		
		/**
		 * Override to provide own functionality
		 */
		protected function customizeBrowserBridge():void
		{
			
		}
		
		private function handleCreationComplete(event:FlexEvent):void
		{
			setupContextMenu();
			initLogging();
				
			browserBridge = new BrowserBridge();
			browserBridge.addEventListener(BrowserBridgeEvent.PRE_INIT, handleBrowserBridgePreInit);
			browserBridge.addEventListener(BrowserBridgeEvent.READY, handleBrowserBridgeReady);
			browserBridge.addEventListener(BrowserBridgeEvent.ERROR, handleBrowserBridgeError);
			
			// TODO Browser may be ready before args are parsed!
			browserBridge.init();
			
			init();
		}
		
		private function initBrowserCookieInterface():void {
			
		}
		
		private function setupContextMenu():void
		{
			var versionContextItem:ContextMenuItem = new ContextMenuItem("Version Information");
			
			versionContextItem.addEventListener(ContextMenuEvent.MENU_ITEM_SELECT, 
				handleVersionContextMenuSelected);
			
			var contextMenu:ContextMenu = new ContextMenu();
			contextMenu.customItems.push(versionContextItem);
			Application.application.contextMenu = contextMenu;
		}

		private function handleVersionContextMenuSelected(event:ContextMenuEvent):void
		{
			displayVersionsDialog();
		}
		
		private function displayVersionsDialog():void
		{
			Alert.show("Build Number: " + BuildNumber.BUILD_NUMBER, 
				"Build Number",
				Alert.OK); 
	
		}
		
		private function handleMouseUp(event:MouseEvent):void
		{
			if (event.ctrlKey && event.altKey)
			{
				displayVersionsDialog();
			}
		}
		
		
		private function initLogging():void
		{
			logger = Log.getLogger(getLoggerName());
			var traceTarget:TraceTarget = new TraceTarget();
			traceTarget.includeCategory = true;
			traceTarget.includeLevel = true;
			
			Log.addTarget(traceTarget);
		}
		
		protected function getLoggerName():String
		{
			throw new Error("Not implemented");
		}
		
		private function handleAuthDialogClose(event:CloseEvent):void
		{
			if (event.detail == Alert.OK)
			{
				var panel:AuthenticationDialog = event.target as AuthenticationDialog;
				var username:String = panel.username;
				var password:String = panel.password;
				var serverAddress:String = panel.serverAddress;
				
				createService(username, password, serverAddress, "http://");
			}
		}
		
		private function createService(username:String, password:String, serverAddress:String, protocol:String = null):void
		{
			var rootURI:String = "/XMLRPCv2/RNA";
			
			service = new XMLRPCService(serverAddress, rootURI, username, password, protocol);
			service.addEventListener(ErrorEvent.ERROR, handleServiceErrorEvent);
			service.addEventListener(XMLRPCServiceEvent.CALL_COMPLETE, handleCallComplete);
			entityManager = new EntityManager(service.getNode(entityManagerURI) as MediatorNode);
			
			if (initialSelectedEntity != null && initialSelectedEntity.length != 0)
			{
				handleEntitySelected(initialSelectedEntity);
			}
		}
		
		private function handleCallComplete(event:XMLRPCServiceEvent):void
		{
			connected = true;
		}
		
		private function handleServiceErrorEvent(event:ErrorEvent):void
		{
			connected = false;
			event.preventDefault();
			
			throw new Error("XMLRPC Error Prevented Throw: " + event.text);
		}
		
		private function handleBrowserBridgePreInit(event:BrowserBridgeEvent):void
		{
			// TODO There's a problem here with the topic not being set before the 
			// browser bridge has had a chance to initialize stuff.
			
			initializeBrowserDepedencies();
		}
		
		private function handleBrowserBridgeReady(event:BrowserBridgeEvent):void
		{
			browserBridge.executeCall("initialize");
		}
		
		private function initializeBrowserDepedencies():void
		{
			
			embedded = browserBridge.args['embedded'] == "1";
			ready = true;
			if (browserBridge.args['topic'] != null)
			{
				topic = browserBridge.args['topic'];
			}
			
			if (browserBridge.args['entity'] != null)
			{
				initialSelectedEntity = StringUtil.trim(browserBridge.args['entity']);
				
				if (initialSelectedEntity.length != 0)
				{
					logger.debug("Showing entity: " + initialSelectedEntity);
					//tiEntityPath.text = initialSelectedEntity;
				}
			}
			
			if (browserBridge.args['entity_manager_uri'] != null)
			{
				entityManagerURI = StringUtil.trim(browserBridge.args['entity_manager_uri']);
				
				if (entityManagerURI.length == 0)
				{
					var message:String = "Empty Entity Manager variable specified";
					
					Alert.show(message, "Critical Error!");
					
					return; 
				}
			}
			else
			{
				entityManagerURI = DEFAULT_ENTITY_MANAGER_URI;
			}
			
			var debugParam:String = StringUtil.trim(browserBridge.args["debug"]).toLowerCase(); 
			if (Boolean(debugParam) && debugParam != "false")
			{
				enableDebug();
			}
			
			logger.debug("Using entity manager URI: '{0}'", entityManagerURI);
			if (browserBridge.isReady)
			{
				// Do not subcribe to topic at the moment.
				//browserBridge.subscribe(topic, handleTopicReceived);
				browserBridge.addCallback("setEntity", handleSetEntity);
				browserBridge.addCallback("getEntity", handleGetEntity);				
				
			}
			
			customizeBrowserBridge();
			
			if (!embedded)
			{
				var authPanel:AuthenticationDialog = AuthenticationDialog.show(this,
					Globals.DEBUG_SERVER_USERNAME, 
					Globals.DEBUG_SERVER_PASSWORD, 
					Globals.DEBUG_SERVER_ADDRESS, handleAuthDialogClose);
			}
			else
			{
				createService(null, null, null);
			}
		}
		
		protected function enableDebug():void
		{
			debug = true;
			
		}
		
		private function handleBrowserBridgeError(event:BrowserBridgeEvent):void
		{
			logger.error("Error loading browser bridge: " +event.message);
			
			Alert.show("JavaScript bridge is not available, widget will be unable to load entities",	 
				"Error" );
			 
			initializeBrowserDepedencies();
		}
		
		/// JAVASCRIPT BRIDGE FUNCTIONS
		public function handleGetEntity(empty:Object=null):String
		{
			if (entity != null)
			{
				return entity.path;
			}
			
			return null;
		}
		
		public function handleSetEntity(entity:String):void
		{
			handleEntitySelected(entity);
		}
		
		private function handleEntitySelected(entityId:String):void
		{
			logger.debug("handleEntitySelected({0})", entityId);
			
			cleanCurrentEntity();

			entity = entityManager.getEntity(entityId);
			
			entitySelected();
		}
		
		protected function entitySelected():void
		{
			if (!entity.propertiesLoaded)
			{
				entity.loadProperties();
			}
			else
			{
				trace("The properties were already loaded");
				trace("\t" + entity.path + ", len=" + entity.properties.length);
				trace(entity.properties);
			}
			
			entity.addEventListener(EntityPropertyChangeEvent.ENTITY_PROPERTY_CHANGE,
				handleEntityPropertyChanged);
			entity.addEventListener(EntityEvent.PROPERTIES_LOADED, 
					handleEntityPropertiesLoaded);
		}
		
		protected function cleanCurrentEntity():void
		{
			if (entity != null)
			{
				entity.removeEventListener(EntityPropertyChangeEvent.ENTITY_PROPERTY_CHANGE, 
					handleEntityPropertyChanged);
				entity.removeEventListener(EntityEvent.PROPERTIES_LOADED, 
					handleEntityPropertiesLoaded);
			}
		}
		
		private function handleEntityPropertiesLoaded(event:EntityEvent):void
		{
			entityPropertiesLoaded();
		
		}
		
		private function handleEntityPropertyChanged(event:EntityPropertyChangeEvent):void
		{
			logger.debug("EntityPropertyChanged: {0}", event);
		}
		
		
		protected function entityPropertyChanged():void
		{
			
		}
		
		protected function entityPropertiesLoaded():void
		{
			
		}
		
		protected function debugLoadEntity(name:String):void
		{
			handleEntitySelected(name);
		}
			
	}
}