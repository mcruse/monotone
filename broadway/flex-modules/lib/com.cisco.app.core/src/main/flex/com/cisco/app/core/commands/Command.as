///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.commands
{
	import com.cisco.app.core.ui.ExecutionEvent;
	import com.cisco.app.core.ui.IHandler;
	
	import flash.events.EventDispatcher;
	
	import mx.events.PropertyChangeEvent;
	
	[Event(name="commandChange", type="com.cisco.app.core.commands.CommandChangeEvent")]
	
	/**
	 * The command framework is central to undo/redo functionality and
	 * is based on the eclipse framework's command framework.
	 * 
	 * A command is a description of some action or an intent of an action
	 * to be executed.  The implementatino does not reside in the command
	 * itself but it merely signals to the system that "something" can
	 * be executed.   
	 * 
	 * Commands are actually executed by handlers, which register with the 
	 * system and tell it what command it is interested in handling.
	 * 
	 * For more information see the IHandler interface.
	 * 
	 * 
	 * @author Robert Cadena
	 */
	public class Command extends EventDispatcher
	{
		/**	
		 * Unique command identifier
		 */
		public var id:String;
		
		private var _name:String;
		
		private var _enabled:Boolean;
		
		private var _handler:IHandler;
		
		private var _defined:Boolean;
		
		public function Command(id:String)
		{
			this.id = id;
		}
		
		//------------------------------------------
		// Public methods
		//------------------------------------------
		
		/**
		 * This executes the command by calling the handler's
		 * <code>execute</code> method.
		 * 
		 * @throws Error if the command is not defined, not enabled, or no handler is present
		 */
		public function execute(executionEvent:ExecutionEvent=null):Object
		{
			if (!_defined || !_enabled)
			{
				throw new Error("Command '" + this.id + "' is not defined or enabled");
			}
			
			if (_handler == null)
			{
				throw new Error("No handler for command '" + this.id + "'");
			}
			
			return _handler.execute(executionEvent);
		}
		
		//------------------------------------------
		// Property getters and setters
		//------------------------------------------
		
		/**
		 * Set the command name.
		 */
		public function set name(value:String):void
		{
			if (_name !== value)
			{
				var oldValue:String = _name;
				this._name = value;
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "name" ,oldValue, _name));
			}
		}
		
		/**
		 * Define the command.  A command cannot be handled if it is not defined.
		 * 
		 * @param name The name to give the command
		 * @param description The command description.
		 */
		public function define(name:String, description:String):void
		{
			this.name = name;
			
			var oldDefined:Boolean = _defined;
			_defined = true;
			
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "defined", oldDefined, _defined));
		}
		
		public function get defined():Boolean
		{
			return _defined;
		}
		
		
		
		public function get enabled():Boolean
		{
			return _enabled;
		}
		
		/**
		 * Flag indicating if the command is enabled.
		 */
		public function set enabled(value:Boolean):void
		{
			if (_enabled !== value)
			{
				var oldValue:Boolean = _enabled;
				this._enabled = value;
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "enabled" ,oldValue, _enabled));
			}
		}
		
		public function get handler():IHandler
		{
			return _handler;
		}
		
		/**
		 * Set the handler for the current command.
		 * 
		 * Dispatches an property change event indicating that
		 * the handler property has changed.
		 * 
		 * It attaches as a listener to the new handler.
		 */
		public function set handler(value:IHandler):void
		{
			if (_handler != null)
			{
				unhookHandler();
			}
			
			if (_handler !== value)
			{
				var oldValue:IHandler = _handler;
				this._handler = value;
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "handler" ,oldValue, _handler));
			}
			
			if (_handler != null)
			{
				hookHandler();
			}
		}
		
		//------------------------------------------
		// Private methods
		//------------------------------------------
		private function unhookHandler():void
		{
			_handler.removeEventListener(PropertyChangeEvent.PROPERTY_CHANGE, handleHandlerPropertyChange);
		}
		
		private function hookHandler():void
		{
			_handler.addEventListener(PropertyChangeEvent.PROPERTY_CHANGE, handleHandlerPropertyChange);
		}
		
		private function handleHandlerPropertyChange(event:PropertyChangeEvent):void
		{
			if (event.property == "enabled")
			{
				updateProperties();
			}
		}
		
		private function updateProperties():void
		{
			if (_handler == null)
			{
				enabled = false;
				return;
			}
			
			enabled = _handler.enabled;
		}
	
	}
}