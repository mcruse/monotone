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
var loader = {};
loader.cleanup = false;
loader.preloads = [];
loader.modules = [];
loader.waitvars = [];
loader.postloads = [];

if (!loader.modules.indexOf) {
	loader.modules.indexOf = function(item) {
		for (var i = 0; i < this.length; i++) {
			if (this[i] == item) return i;
		}
		return -1;
	}
}

loader.add_preload = function(func) {
	loader.preloads.push(func);
}

loader.add_module = function(path, container, varname) {
	if (loader.modules.indexOf(path) == -1) loader.modules.push(path);
	if (container && varname) loader.waitvars.push([container, varname]);
}

loader.add_postload = function(func) {
	loader.postloads.push(func);
}

loader.run = function() {
	// Utility functions.
	function loader_for(module) {
		return function() {load_module(module);};
	}
	function load_module(module) {
		var body = document.getElementsByTagName('body')[0];
		var script = document.createElement('script');
		script.setAttribute('src',module);
		script.setAttribute('type','text/javascript');
		script.setAttribute('language','Javascript');
		body.appendChild(script);
	}

	function setup_preloaders(preloads) {
		return preloads.slice(0);
	}

	function setup_module_loaders(modules) {
		var module_loaders = new Array();
		for (var i = 0; i < modules.length; i++) {
			module_loaders.push(loader_for(modules[i]));
		}
		return module_loaders;
	}

	function setup_postloaders(postloads) {
		return postloads.slice(0);
	}

	function runloaders(loaders) {
		while (loaders.length)
			loaders.shift()();
	}

	function runpostloaders(postloaders) {
		var waitvars = loader.waitvars.slice(0);
		function run_if_loaded() {
			function is_finished_loading() {
				while (waitvars.length) {
					var varowner = waitvars[0][0];
					var varname = waitvars[0][1];
					if (typeof(varowner[varname]) != 'undefined') {
						waitvars.shift();
					} else return false;
				}
				return true;
			}
			if (is_finished_loading())
				runloaders(postloaders);
			else window.setTimeout(run_if_loaded, 250);
		}
		run_if_loaded();
	}

	function cleanup() {
		for (var name in loader) {
			delete loader[name];
		}
	}

	var loaders = new Array();
	var postloaders = new Array();
	loaders = loaders.concat(setup_preloaders(loader.preloads));
	loaders = loaders.concat(setup_module_loaders(loader.modules));
	postloaders = postloaders.concat(setup_postloaders(loader.postloads));
	if (loader.cleanup) postloaders.push(cleanup);

	runloaders(loaders);
	runpostloaders(postloaders);
}

window.onload = loader.run;
