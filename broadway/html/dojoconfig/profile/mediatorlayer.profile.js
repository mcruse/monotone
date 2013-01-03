dependencies = {
	layers:[
			
			//Our target mediatorlayer
			{
				name: "../dojoconfig/mediator_layer.js",
				dependencies: [
					"dojoconfig.includes.mediator_includes",
					"dijit",
					"dojox",
					"utils",
					"nbmweb"	
					],
				layerDependencies:[
			    ]
			}
			],
	prefixes: [
		[ "dijit", "../dijit" ],
		[ "dojox", "../dojox" ],
		[ "dojoconfig", "../../html/dojoconfig" ],
		["utils","../../html/public/utils"],
		["util","../../opt/cisco/nbm"],
		["nbmweb","../../html/public/nbmweb"],
		["mpx","../../html/mpx"]		
	]
}
