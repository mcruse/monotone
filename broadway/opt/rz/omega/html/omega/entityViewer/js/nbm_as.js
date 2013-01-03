/*
Copyright (C) 2010 2011 Cisco Systems

This program is free software; you can redistribute it and/or         
modify it under the terms of the GNU General Public License         
as published by the Free Software Foundation; either version 2         
of the License, or (at your option) any later version.         
    
This program is distributed in the hope that it will be useful,         
but WITHOUT ANY WARRANTY; without even the implied warranty of         
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         
GNU General Public License for more details.         
    
You should have received a copy of the GNU General Public License         
along with this program; if not, write to:         
The Free Software Foundation, Inc.         
59 Temple Place - Suite 330         
Boston, MA  02111-1307, USA.         
    
As a special exception, if other files instantiate classes, templates  
or use macros or inline functions from this project, or you compile         
this file and link it with other works to produce a work based         
on this file, this file does not by itself cause the resulting         
work to be covered by the GNU General Public License. However         
the source code for this file must still be made available in         
accordance with section (3) of the GNU General Public License.         
    
This exception does not invalidate any other reasons why a work         
based on this file might be covered by the GNU General Public         
License.
*/
cisco = function()
{
	
}

cisco.NBMBridge = function()
{
	
}

cisco.NBMBridge = {
		widgets : {},
		
		loaded : function(id)
		{
			
			var widget = cisco.NBMBridge.widgets[id];
			
			if (widget != null)
			{
				widget.loaded();
			}
		},
		
		isReady : function()
		{
			return true;
		},
		
		createWidget : function(swfUrlStr, replaceElemIdStr, /* String */ name_id, widthStr, heightStr, flashvarsObj, parObj, attObj)
		{
			attObj.id = name_id;
			attObj.name = name_id;
			
			var widget = new NBMWidget(name_id)
			
			cisco.NBMBridge.widgets[name_id] = widget;
			
			swfobject.embedSWF(swfUrlStr,
			replaceElemIdStr, widthStr, heightStr, "9.0.0",
			false, flashvarsObj, parObj, attObj);
			
			return widget;
		},
		
		
		_addExternalInterfaceCallback : function(id, methodName)
		{
			var widget = cisco.NBMBridge.widgets[id];
			
			widget._registerCallback(methodName)
		},
		
		/**
		 *  Called from flex NBMWidget proxy to this widget proxy
		 */
		_call : function(id, methodName, args)
		{
			var widget = cisco.NBMBridge.widgets[id];
			
			if (widget != null)
			{
				widget[methodName].apply(widget, args);
			}
			else
			{
				alert("no such widget: " + id)
			}
		}
}



function NBMWidget(id)
{
	this._initialize(id)
}

NBMWidget.prototype = {
		
	ready: false,
	movie: null, 
	id: null,
	_subscription_handles : {},
	listeners: [],
	
	_registerCallback : function(methodName)
	{
		this[methodName] = function(args)
		{
			this.execute(methodName, args);
		}
	},
	
	subscribe : function(topic, methodName)
	{
		this._registerCallback(methodName);
		
		var handle = dojo.subscribe(topic, this, methodName)
		
		this._subscription_handles[topic + "_" + methodName] = handle;
		                           
		
	},
	
	unsubscribe : function(topic, methodName)
	{
		var handle = this._subscription_handles[topic + "_" + methodName];
		
		dojo.unsubscribe(handle);
	},

	_initialize: function(id)
	{
		this.id = id;
	},
	
	initialize : function()
	{
		this.ready = true;
		
		var i = 0;
		
		for (i = 0; i < this.listeners.length; i++)
		{
			try
			{	
				this.listeners[i]()
			}
			catch (e)
			{
				alert("Error executing listener:"  + e);
			}
		}
		this.listeners = [];
		
	},
	
	swfObjectLoaded : function(e)
	{
		
	},
	
	addLoadedListener: function(/* Function */ listener) 
	{
		if (this.ready)
		{
			listener();
		}
		else
		{
			this.listeners.push(listener);
		}
	},
			
	isReady : function()
	{
		return this.ready;
	},
	
	execute : function(methodName, args)
	{
		return this.movie[methodName](args);
	},
			
	loaded : function()
	{
		this.movie = dojo.byId(this.id);
	
		if (this.movie != null)
		{
			//this.execute("testOutside", "one");
		}
	}
	
}	

