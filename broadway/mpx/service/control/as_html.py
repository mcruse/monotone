"""
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
"""
import string

def app_drawing_to_html(app_drawing, live=1):
    html = []
    html.extend(head(app_drawing, live))

    html.append('''<body ID="monitorDrawing" name="monitorDrawing" bgcolor="#000000" STYLE="font-family: monospace;">
<DIV id=WebExpressPageProps style="DISPLAY: none; VISIBILITY: hidden; POSITION: absolute" refreshrate="2000" refreshtype="fixed" cache="false" backoff="120000"></DIV>
''')
    html.append('<div style="position:absolute; width:%dpx; height:%dpx; z-index:0; left: 0px; top: 0px"></div>' % \
                (app_drawing.graphic_width(), app_drawing.graphic_height()))

    html.extend(template_images(app_drawing))
    html.extend(references(app_drawing, live))
    html.extend(constants(app_drawing))
    html.extend(connections(app_drawing))
    #html.extend(jumps(app_drawing))
    if live:
        html.extend(point_displays(app_drawing))
    html.extend(animations(app_drawing))
    html.append('''
<!-- *************** END ************************* -->
</body>
</html>
''')
    return string.join(html,'')

def head(app_drawing, live):
    html = []
    html.append('''<html>
<head>
<title>%s</title>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
<style>
<!--.rzpoint { font-family: Courier New; font-size: 12pt; color: #FFFFFF; text-align: Center; width: 55px; height: 20px; position: absolute; background-color: %s; layer-background-color: %s; border: 1px none #000000 }
-->
.rztemplatename {  font-family: "Courier New", Courier, mono; font-size: 14px; font-style: normal; line-height: normal; font-weight: normal; font-variant: normal; color: #FFFFFF; text-decoration: none; position:absolute; border-width: 0px; }
</style>''' % (app_drawing.name, app_drawing.font.background_color_name, app_drawing.font.background_color_name))
    if live:
        html.append('''
<script src="/webapi/js/sdk2.js" type="text/javascript"></script>
<script src="/webapi/js/pagerefresh.js" type="text/javascript" webexpress="true"></script>
<script src="/webapi/js/widget.js" type="text/javascript" webexpress="true"></script>
<script src="/webapi/js/GenericNode.wjs" type="text/javascript" widget="true"></script>
<script src="/webapi/js/GenericLabel.wjs" type="text/javascript" widget="true"></script>
<script src="/webapi/js/GenericNodeBox.wjs" type="text/javascript" widget="true"></script>
<script src="/webapi/js/GenericLabelBox.wjs" type="text/javascript" widget="true"></script>
<SCRIPT language=JavaScript src="/webapi/js/PHVirtualPoint.wjs" type=text/javascript widget="true"></SCRIPT>
<SCRIPT language=JavaScript src="/webapi/js/PHJump.wjs" type=text/javascript widget="true"></SCRIPT>
<SCRIPT language=JavaScript src="/webapi/js/PHAnimation.wjs" type=text/javascript widget="true"></SCRIPT>
<SCRIPT language=JavaScript src="/webapi/js/PHSchedule.wjs" type=text/javascript widget="true"></SCRIPT>
</head>''')
    return html

def connections(app_drawing):
    z = 1000
    html = []
    html.append('''
<!-- ******* CONNECTIONS ******* -->
''')
    connections = app_drawing.connections
    #convert connections to line segments
    t = 'end'
    lines = []
    for c in connections:
        t = c['type']
        x = int(c['x'])
        y = int(c['y'])
        if t == 'begin':
            x1 = x
            y1 = y
        elif t == 'turn':
            width = abs(x1 - x) + 1
            height = abs(y1 - y) + 1
            left = min(x1, x)
            top = min(y1, y)
            lines.append((left,top,width,height))
            x1 = x
            y1 = y
        elif t == 'end':
            width = abs(x1 - x) + 1
            height = abs(y1 - y) + 1
            left = min(x1, x)
            top = min(y1, y)
            lines.append((left,top,width,height))
        else:
            raise
    for line in lines:
        z += 1
        left,top,width,height = line
        html.append('''
<div id="Connection%d" style="position:absolute; width:%dpx; height:%dpx; z-index:%d; left: %dpx; top: %dpx"><img src="/images/1x1.png" width="%d" height="%d" style="VERTICAL-ALIGN: top;"> </div>
''' % (z, width, height, z, left, top, width, height))
    return html


def animations(app_drawing):
    z = 3000
    html = []
    html.append('''
<!-- *************** ANIMATIONS ************************* -->
''')
    return html

def references(app_drawing, live):
    z = 0 #5000
    html = []
    html.append('''
<!-- ******* REFERENCE IMAGES ******* -->
''')
    cw = app_drawing.font.width
    ch = app_drawing.font.height
    for r in app_drawing.references: #track down the reference and add it's outputs to the outputs_connections map
        z += 1
        ref_name = r['name'].replace('%2F','/')
        split_ref = ref_name.split('/')
        ref_app = split_ref[1]
        ref_drawing_name = split_ref[2]
        def_name = r['template_name']
        def_node = app_drawing.get_template_definition_node(def_name)
        image_name = def_node.graphic_name()
        h = def_node.graphic_height()
        w = def_node.graphic_width()
        x = int(r['x'])
        y = int(r['y'])
        ##TODO shade reference image somehow to make it darker
        #Image
        html.append('''
<div id="reference%d" style="position:absolute; width:%dpx; height:%dpx; z-index:%d; left: %dpx; top: %dpx; filter:alpha(opacity=40); opacity:.40;"><a href="/perfect_host.psp?app=%s&drawing=%s&live=%d"><img src="/template_images/%s" width="%d" height="%d" align="left"  border="0" ></a></div>
''' % (z, w, h, 5000+z, x, y, ref_app, ref_drawing_name, live, image_name, w, h))
        # Name
        name_width = cw * len(ref_name)
        html.append('''
<div id="tmp_name%d" class=rztemplatename style="width:%dpx; height:%dpx; z-index:%d; left: %dpx; top: %dpx; "><a href="/perfect_host.psp?app=%s&drawing=%s&live=%d">%s</a></div>
''' % (z, name_width + 4, ch, 5000+z, x+((w-name_width)/2), y-ch-5, ref_app, ref_drawing_name, live, ref_name))
        # JUMP


    return html

def constants(app_drawing):
    z = 0
    html = []
    html.append('''
<!-- ******* CONSTANTS ******* -->
''')
    constants = app_drawing.constants
    cw = app_drawing.font.width
    h = app_drawing.font.height
    for c in constants: #a list of dictionarys
        z += 1
        v = c['value']
        w = cw * len(v) + 4
        x = int(c['x']) - w - 5 #still need a little line segment
        y = int(c['y']) - h/2 - 2
        html.append('''
<div id="constant%d" style="position:absolute; width:%dpx; height:%dpx; z-index:%d; left: %dpx; top: %dpx; VERTICAL-ALIGN: top; border-width: 1px; border-style: solid; border-color: white; color: white">%s</div>
''' % (z,w,h,4000+z,x,y,v))

    return html
def template_images(app_drawing):
    z = 0 #z index starts at 6000, but template id's start at 1
    html = []
    html.append('''
<!-- ******* TEMPLATE IMAGES ******* -->
''')
    templates = app_drawing.get_templates()
    cw = app_drawing.font.width
    ch = app_drawing.font.height
    for t in templates:
        z += 1
        n = t.graphic_name()
        h = t.graphic_height()
        w = t.graphic_width()
        # IMAGE
        html.append('''
<div id="template%d" style="position:absolute; width:%dpx; height:%dpx; z-index:%d; left: %dpx; top: %dpx"><img src="/template_images/%s" width="%d" height="%d" align="left"  border="0"></div>
''' % (z,w,h,6000+z,t.x,t.y,n,w,h))
        # NAME
        if len(t.name) > 1 and (t.name[0] != '.'):
            name_width = cw * len(t.name)
            html.append('''
<div class=rztemplatename id="tmp_name%d" style="width:%dpx; height:%dpx; z-index:%d; left: %dpx; top: %dpx; ">%s</div>
''' % (z, name_width + 4, ch, 6000+z, t.x+((w-name_width)/2), t.y-ch-5, t.name.replace('%2F','/')))

    return html


def point_displays(app_drawing):
    z = 7000
    html = []
    html.append('''
<!-- ************  POINT DISPLAYS  ********* -->
''')

    templates = app_drawing.get_templates()
    for t in templates:
        z += 1
        n = t.name
        if n.find('.') != 0:
            html.append(template_as_html(t,z))
    #still need to handle special templates like timeclocks and alarms, etc
    return html

def template_as_html(template, z):
    nodeReference = template.as_node_url()
    return '''
<DIV id=value_%s style="BORDER-RIGHT: 0px; BORDER-TOP: 0px; Z-INDEX: %d; LEFT: %dpx; BORDER-LEFT: 0px; WIDTH: auto; CURSOR: auto; BORDER-BOTTOM: 0px; POSITION: absolute; TOP: %dpx; HEIGHT: auto" widget="PHVirtualPoint" version="1_0_dev_2" zindex="%d" overflow="visible" pos_rel="false">

<DIV style="FONT-WEIGHT: %s; FONT-SIZE: %dpx; LEFT: 0px; VERTICAL-ALIGN: top; WIDTH: auto; COLOR: %s; FONT-STYLE: %s; FONT-FAMILY: %s, Verdana, Arial, Helvetica, sans-serif; POSITION: relative; TOP: 0px; HEIGHT: auto; BACKGROUND-COLOR: %s; TEXT-ALIGN: left" element="outercontainer">

<DIV style="DISPLAY: none; LEFT: 0px; VISIBILITY: hidden; WIDTH: 1px; TOP: 0px; HEIGHT: 1px; BACKGROUND-COLOR: transparent" element="info" type="hidden" display_character_length="8" override_enabled="%s" override_active="false" units="%s" upper_alarm_threshold="%d" upper_warning_threshold="%d" lower_warning_threshold="%d" lower_alarm_threshold="%d" offline_color="lightgrey" normal_color="%s" warning_color="yellow" alarm_color="red" override_color="blue" pulse_length="1000"></DIV>

<DIV style="Z-INDEX: 1; LEFT: 0px; VERTICAL-ALIGN: top; WIDTH: auto; POSITION: relative; TOP: 0px; HEIGHT: auto; BACKGROUND-COLOR: transparent " element="textcontainer">

<DIV style="Z-INDEX: 1; LEFT: 0px; VISIBILITY: hidden; VERTICAL-ALIGN: top; TOP: 0px; BACKGROUND-COLOR: transparent" element="placeholder">XXXXXXXX</DIV>

<DIV style="Z-INDEX: 2; LEFT: 0px; VERTICAL-ALIGN: top; POSITION: absolute; TOP: 0px; BACKGROUND-COLOR: transparent" element="nodedisplay" node="%s/_status" display_function="PHVirtualPointDisplayReal">###</DIV>

<DIV ondblclick=PHVirtualPointOpenOverrideDialog(event) style="BORDER-RIGHT: 0px; PADDING-RIGHT: 0px; BORDER-TOP: 0px; PADDING-LEFT: 0px; Z-INDEX: 3; LEFT: 0px; BACKGROUND-IMAGE: url(/webapi/images/cleardot.gif); PADDING-BOTTOM: 0px; MARGIN: 0px; VERTICAL-ALIGN: left; BORDER-LEFT: 0px; WIDTH: auto; PADDING-TOP: 0px; BORDER-BOTTOM: 0px; BACKGROUND-REPEAT: repeat; POSITION: absolute; TOP: 0px; HEIGHT: auto; BACKGROUND-COLOR: transparent" element="hitareacontainer">

<DIV style="LEFT: 0px; VISIBILITY: hidden; VERTICAL-ALIGN: top; TOP: 0px; BACKGROUND-COLOR: transparent" element="hitarea">XXXXXXXX</DIV></DIV></DIV></DIV></DIV>''' % \
            (template.name, z, template.x, template.y-1, z, template.font.weight, \
             template.font.height, template.font.color_name, template.font.italic, \
             template.font.face_name, template.font.background_color_name, \
             template.allow_overrides, template.units, template.upper_alarm_threshold, \
             template.upper_warning_threshold, template.lower_warning_threshold, \
             template.lower_alarm_threshold, template.font.background_color_name, \
             template.as_node_url()) 
