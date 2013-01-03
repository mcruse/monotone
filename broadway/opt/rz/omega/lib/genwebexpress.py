"""
Copyright (C) 2008 2009 2010 2011 Cisco Systems

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
# genwebexpress -- Python module to generate WebExpress web page
# Copyright (c) 2005 Richards-Zeta
# $Name: mediator_3_1_2_branch $
# $Id: genwebexpress.py 20606 2011-06-22 10:50:27Z jchaudhu $

import os
import sys
from mpx import properties
from mpx.lib import rzutils

def testmessage():
    message = 'Test Message from inside genwebexpress module\n'
    return message

def testApplicationAllowed():
    return rzutils.isApplicationAllowed('webexpress')

def addActiveHardware():
    html_snippit = """\
<!-- begin activehardware rev 2 -->
<div id="activehardware">
  <table border="0" cellpadding="0" cellspacing="0">
    <tr align="left">
      <td width="119" valign="top">

      </td>
      <td valign="top" nowrap >
        <iframe src="/webapi/psp/mediatorname.psp" name="nameframe"
                marginwidth="0" marginheight="0" scrolling="no"
                frameborder="0">
        </iframe>
      </td>
    </tr>
  </table>
</div>
 <!-- end activehardware rev 2 -->
"""
    return html_snippit

def addDynamicEditPane():
    # @note The width and height is adjusted by 8 to account for the document
    #       "margin" that I can't account for programmatically.
    # @note The width and height is adjusted by 4 to account for the "border"
    #       of 2 that I can't account for programmatically.
    # @note Without the 8 and 4 pixel adjustments, IE 7 creates scrollbars
    #       even though they don't seem strictly required.
    # @note The editFrame is forced to 10px high so FF calculates the
    #       window_height correctly.
    # @note The max of document.body.clientHeight/Width and
    #       document.documentElement.clientHeight/Width SHOULD work for IE
    #       in both quirksmode and strict mode.  SHOULD.
    html_snippet = """\
        <link rel="stylesheet" href="/public/styles/page.css" type="text/css">
        <link rel="stylesheet" href="/public/styles/tabs.css" type="text/css">
        <link rel="stylesheet" href="/public/styles/pagination.css" type="text/css">
        <link rel="stylesheet" href="/public/styles/events.css" type="text/css">
        <link rel="stylesheet" href="/public/styles/configuration.css" type="text/css">
        <link rel="stylesheet" type="text/css" href="/dojoroot/dojo/resources/dojo.css" />
        <link rel="stylesheet" type="text/css" href="/dojoroot/dijit/themes/dijit.css" />
        <link rel="stylesheet" type="text/css" href="/dojoroot/dijit/themes/tundra/tundra.css" />
        <link rel="stylesheet" type="text/css" href="/cues/themes/kubrick/layout.css" />
        <link rel="stylesheet" type="text/css" href="/cues/themes/kubrick/tabs.css" />
        <script type="text/javascript">
            djConfig = {
                isDebug: false,
                debugAtAllCosts: false,
                parseOnLoad: true,
                baseUrl: "/dojoroot/dojo/",
                modulePaths: {
                    mpx: '/mpx',
                    cues: '/cues',
                    utils: '/public/utils'
                }
            };
        </script>
        <script type="text/javascript" src="/dojoroot/dojo/dojo.js"></script>
        <script type="text/javascript" src="/dojoroot/dojoconfig/mediator_layer.js"></script>
<script type="text/javascript">
dojo.require("utils.style");
accumulated_offset = function (element, attribute) {
  var total_offset = element[attribute];
  if (element.offsetParent == null) {
    return total_offset;
  }
  return total_offset + accumulated_offset(element.offsetParent,attribute);
}
window.adjustEditPane = function () {
  var edit_pane_td = document.getElementById("editFrameHolder");
  if (!edit_pane_td)
      return;
  var edit_pane_iframe = document.getElementById("editFrame");
  edit_pane_td.height = 10;
  edit_pane_iframe.height = 10;
  var window_height = Math.max(document.body.clientHeight,
                               document.documentElement.clientHeight);
  var window_width = Math.max(document.body.clientWidth,
                              document.documentElement.clientWidth);
  var total_top_offset = accumulated_offset(edit_pane_iframe, "offsetTop");
  var total_left_offset = accumulated_offset(edit_pane_iframe, "offsetLeft");
  var pane_width =  window_width - total_left_offset - 8 - 4;
  var pane_height =  Math.max(window_height - total_top_offset - 8 - 4,
                              edit_pane_td.parentNode.clientHeight - 2);
  edit_pane_td.width = pane_width;
  edit_pane_td.height = pane_height;
  edit_pane_iframe.width = pane_width;
  edit_pane_iframe.height = pane_height;
  return;
}
var resizeConnection = dojo.connect(
    window, "onresize", function() {window.adjustEditPane();});
</script>
"""
    return html_snippet

def makeSecondPageEnabled(root, qsdict):
    thePage = []
    if not rzutils.isApplicationAllowed('webexpress'):
        return makeSecondPageDisabled(root, qsdict)
    #set query string defaults
    file = ''
    showallfiles = 'false'
    #override with query string values
    if qsdict.has_key('file'):
        file= '/%s' % qsdict['file']
    if qsdict.has_key('showallfiles'):
        showallfiles = '%s' % qsdict['showallfiles']

    #start generation of document
    thePage.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html14/loose.dtd">')
    thePage.append('<html>')
    #generate document head
    thePage.append('<head>')
    thePage.append('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">')
    thePage.append('<meta http-equiv="pragma" content="no-cache">')
    thePage.append('<meta http-equiv="cache-control" content="no-cache">')
    thePage.append('<link rel="stylesheet" href="/public/styles/page.css" type="text/css">')
    thePage.append('<script language="JavaScript1.3" type="text/javascript" src="/webapi/js/sdk2.js"></script>')
    thePage.append('<script src="/webapi/js/webexpress.js" type="text/javascript"></script>')
    thePage.append('<!-- Widget files -->')
    thePage.append('<script language="JavaScript1.3" type="text/javascript" src="/webapi/js/widget.js"></script>')
    #add script to include all widgets
    thePage.extend(rzutils.genWidgetScript(root))
    thePage.append(addDynamicEditPane())
    thePage.append('</head>')
    # generate document body
    thePage.append('<body class="kubrick tundra">')
    thePage.append('<div id="background"><img src="/public/images/pageBackground.jpg" /></div>')
    thePage.append('<div id="header">')
    thePage.append('<h1 class="title">Network Building Mediator</h1>')
    thePage.append('<ul class="actions">')
    thePage.append('<li><a href="">About</a></li>')
    thePage.append('<li><a id="logout" href="/logout"> Logout </a></li>')
    thePage.append('</ul>')
    thePage.append('</div>')
    thePage.append("""
        <div id="primary-tabs"
            title=""
            class="primary-tabs"
            href="/public/templates/primary.html"
            extractContent="false"
            preventCache="false"
            dojoType="dijit.layout.ContentPane"
            onDownloadEnd="dojo.addClass('webexpress-tab-button', 'selected');" >
        </div>""")
    thePage.append('<div id="stage">')
    thePage.append('<div class="pane" id="navigation-pane">')
    thePage.append('<div>')
    thePage.append('<div class="navigation-menu">')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('<div id="contentarea" class="pane" vAlign="center">')
    thePage.append('<table cellspacing="0" cellpadding="0" border="0"  width="938" height="30">')
    thePage.append('<tr>')
    thePage.append('<td></td>')
    thePage.append('<td valign="top">')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table border="0" cellspacing="0" cellpadding="0">')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table border="0" bgcolor="white" cellpadding="0" cellspacing="0">')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('</td><td bgcolor="#33a0cd" class="white">&nbsp;&nbsp;&nbsp;MESSAGES&nbsp;</td>')
    thePage.append('<td>')
    thePage.append('<table cellpadding="0"  width="250" height="25" border="0">')
    thePage.append('<tr>')
    thePage.append('<td style="text-align:left;vertical-align:top" class="smalltext" id="msg">&nbsp;</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('<td align="center">')
    thePage.append('<table>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table>')
    thePage.append('<tr>')

    thePage.append('<td><a href="javascript:WebExpress_SaveFileWin();"><img src="/webapi/images/button_saveFile2.png" width="91" height="29" alt="" border="0"></a></td>')
    thePage.append('<td><a href="javascript:WebExpress_LaunchHelp();">'
                   '<img src="/webapi/images/button_help2.png"'
				   'width="91" height="29"alt="" border="0">'
                   '</a></td>')
    thePage.append('<td><a href="/omega/webexpress/index.html">'
                   '<img src="/webapi/images/button_back2.png"'
				   'width="91" height="29" alt="" border="0">'
                   '</a></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('<br>')
    thePage.append('<table cellspacing="0" cellpadding="0" border="0">')
    thePage.append('<tr>')
    thePage.append('<td valign="top" align="center">')
    thePage.append('<table  width="150" border="0" cellspacing="0" cellpadding="0" >')
    thePage.append('<tr>')
    thePage.append('<td nowrap><img src="/webapi/images/spacer.gif" width="1" height="20" alt="" border="0">&nbsp;&nbsp;Add or Delete Widgets:</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td nowrap><img src="/webapi/images/spacer.gif" width="1" height="10" alt="" border="0">&nbsp;</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td colspan="4" valign="bottom" align="center">')
    thePage.append('<select name="WebExpressWidgets" class="webexpressselect" id="WebExpressWidgets" disabled>')
    thePage.append('<option value="" SELECTED>Please select a widget</option>')
    thePage.append('</select></td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td><img src="/webapi/images/spacer.gif" width="1" height="10" alt="" border="0">&nbsp;</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table cellspacing="1" cellpadding="1" border="0" align="center">')
    thePage.append('<tr>')
    thePage.append('<td rowspan="2"><img src="/webapi/images/button_create2.png" width="65" height="28" alt="" border="0" style="cursor:pointer; padding:0px 6px;" onclick="WebExpress_CreateWidget()"></td>')
    thePage.append('<td rowspan="2"><img src="/webapi/images/button_copy2.png" width="65" height="28" alt="" border="0"  onclick="WebExpress_CopyWidget()"></td>')
    thePage.append('<td rowspan="2"><img src="/webapi/images/button_delete2.png" width="65" height="28" alt="" border="0" onclick="WebExpress_DeleteWidget()"></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td nowrap><img src="/webapi/images/spacer.gif" width="1" height="30" alt="" border="0">&nbsp;&nbsp;Selected Widget:</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td class="smalltext" valign="top">&nbsp;&nbsp;&nbsp;&nbsp;Type:&nbsp;<span class="smalltext" id="widget_type">&nbsp;</span></td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td class="smalltext" valign="top">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ID:&nbsp;<span class="smalltext" id="widget_id">&nbsp;</span></td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td nowrap><img src="/webapi/images/spacer.gif" width="1" height="30" alt="" border="0">&nbsp;&nbsp;Position Widget:</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table>')
    thePage.append('<tr>')
    thePage.append('<td width="70%" align="right" class="smalltext" valign="top">Z-Index:</td>')
    thePage.append('<td width="30%"><input type="text" id="zaxis" size="3"></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table>')
    thePage.append('<tr>')
    thePage.append('<td  width="70%" align="right" class="smalltext" valign="top">X Coordinate:</td>')
    thePage.append('<td width="30%"><input type="text" id="xaxis" size="3"></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table>')
    thePage.append('<tr>')
    thePage.append('<td  width="70%" align="right" class="smalltext" valign="top">Y Coordinate:</td>')
    thePage.append('<td width="30%" ><input type="text" id="yaxis" size="3"></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table>')
    thePage.append('<tr>')
    thePage.append('<td nowrap><img src="/webapi/images/spacer.gif" width="1" height="30" alt="" border="0">&nbsp;&nbsp;Configure Page:</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td width="50%" align="right" class="smalltext" valign="top">&nbsp;&nbsp;&nbsp;Refresh Page:</td>')
    thePage.append('<td width="50%" ><input type="text" id="pagerefresh" size="9" readonly></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('<tr>')
    thePage.append('<td align="center" valign="top"><img src="/webapi/images/spacer.gif" width="1" height="40" alt="" border="0"><img src="/webapi/images/button_configure2.png" width="91" height="29" alt="" border="0"  onclick="WebExpress_ConfigurePage()"></td>')
    thePage.append('</tr>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td bgcolor="#97B1D0"><a href="/index.html"></a></td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td align="center" valign="top" bgcolor="#97B1D0"></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('<td>&nbsp;</td>')
    thePage.append('<td id="editFrameHolder" colspan="3" width="730" valign="top" border="0" editFile="%s"></td>' % (file))
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</div>')
    # Force bgcolor so FF acts like IE.  I don't know which one is actually right.
    thePage.append('<script type="text/javascript">')
    thePage.append('WebExpress_start();')
    thePage.append('</script>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</body>')
    thePage.append('</html>')
    return thePage

def makeFirstPageDisabled(root, qsdict):
    thePage = []
    #set query string defaults
    file = ''
    showallfiles = 'false'
    #override with query string values
    if qsdict.has_key('file'):
        file= '/%s' % qsdict['file']
    if qsdict.has_key('showallfiles'):
        showallfiles = '%s' % qsdict['showallfiles']
    #start generation of document
    thePage.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html14/loose.dtd">')
    thePage.append('<html>')
    #generate document head
    thePage.append('<head>')
    thePage.append('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">')
    thePage.append('<meta http-equiv="pragma" content="no-cache">')
    thePage.append('<meta http-equiv="cache-control" content="no-cache">')
    thePage.append('<link rel="stylesheet" href="/public/styles/navigation.css" type="text/css">')
    thePage.append('<script language="JavaScript1.3" type="text/javascript" src="/webapi/js/sdk2.js"></script>')
    thePage.append('<script src="/webapi/js/webexpress.js" type="text/javascript"></script>')
    thePage.append('<!-- Widget files -->')
    thePage.append('<script language="JavaScript1.3" type="text/javascript" src="/webapi/js/widget.js"></script>')
    #add script to include all widgets
    thePage.extend(rzutils.genWidgetScript(root))
    thePage.append(addDynamicEditPane())
    thePage.append('</head>')
    # generate document body
    thePage.append('<body class="kubrick tundra">')
    thePage.append('<div id="background"><img src="/public/images/pageBackground.jpg" /></div>')
    thePage.append('<h1 class="title">Network Building Mediator</h1>')
    thePage.append('<ul class="actions">')
    thePage.append('<li><a href="">About</a></li>')
    thePage.append('<li><a id="logout" href="/logout"> Logout </a></li>')
    thePage.append('</ul>')
    thePage.append('</div>')
    thePage.append("""
        <div id="primary-tabs"
            title=""
            class="primary-tabs"
            href="/public/templates/primary.html"
            extractContent="false"
            preventCache="false"
            dojoType="dijit.layout.ContentPane"
            onDownloadEnd="dojo.addClass('webexpress-tab-button', 'selected');" 
            addOnUnload=WebExpress_ConfirmExit;>
        </div>""")
    thePage.append('<div id="stage">')

    thePage.append('<div class="pane" id="navigation-pane">')
    thePage.append('<div>')
    thePage.append('<div class="navigation-menu">')

    thePage.append('<ul class="button-menu">')
    thePage.append('<li class="button">')
    thePage.append('<a href="javascript:WebExpress_FileOpsNew()">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('Create New File')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append('<li class="button">')
    thePage.append('<a href="javascript:WebExpress_FileOpsView()">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('View Selected File')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append('<li class="button">')
    thePage.append('<a href="javascript:WebExpress_FileOpsEdit()">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('Edit Selected File')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append('<li class="button">')
    thePage.append('<a href="javascript:WebExpress_FileOpsDelete()">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('Delete Selected File')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append('<li class="button">')
    thePage.append('<a href="javascript:WebExpress_FileOpsCopyMultiple()">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('Copy Multiple Files')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append('<li class="button">')
    thePage.append('<a href="javascript:WebExpress_FileOpsDeleteMultiple()">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('Delete Multiple Files')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append('<li class="button">')
    thePage.append('<a href="fileupload.html">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('Upload A File')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append( '</ul>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</div>')

    thePage.append('<div id="contentarea" class="pane"  align="center" >')

    thePage.append('<table style="margin-top: 75px;">')
    thePage.append('    <tr valign="baseline">')
    thePage.append('        <td>WebExpress allows you to make customized web pages, with real-time data, that get served up by the Cisco Network Building Mediator.</td>')
    thePage.append('        <td>&nbsp;&nbsp;')
    #add script for file selector
    thePage.extend(rzutils.genFileSelectorScript(root,'*.htm;*.html',showallfiles))
    thePage.append('        </td>')
    thePage.append('   </tr>')
    thePage.append('</table>')

    thePage.append('<script type="text/javascript">')
    thePage.append('function WebExpress_FileOpsEdit(){')
    thePage.append('var f = document.getElementById("theFile").value;')
    thePage.append('top.location = "/omega/webexpress/webexpress.psp?showallfiles=%s&file=" + f;' % (showallfiles))
    thePage.append('}')
    thePage.append('function WebExpress_FileOpsNew(){')
    thePage.append('top.location = "/omega/webexpress/webexpress.psp?showallfiles=%s&file=NEWFILE";' % (showallfiles))
    thePage.append('}')
    thePage.append('function WebExpress_FileOpsDeleteMultiple(){')
    thePage.append('top.location = "/omega/webexpress/deletemultiple.html?showallfiles=%s";' % (showallfiles))
    thePage.append('}')
    thePage.append('function WebExpress_FileOpsCopyMultiple(){')
    thePage.append('top.location = "/omega/webexpress/copymultiple.html?showallfiles=%s";' % (showallfiles))
    thePage.append('}')
    thePage.append('function WebExpress_FileOpsDisabled(){')
    thePage.append('alert("This feature is disabled in this Omega version. Please contact your vendor for upgrade information.");')
    thePage.append('}')
    thePage.append('function WebExpress_ConfirmExit(){')
    thePage.append('alert(“You have not saved the form yet. Are you sure ?”);')
    thePage.append('}')
    thePage.append('</script>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</body>')
    thePage.append('</html>')
    return thePage

def makeFirstPageEnabled(root, qsdict):
    thePage = []
    #extra check to prevent user calling this function directly
    if not rzutils.isApplicationAllowed('webexpress'):
        return makeFirstPageDisabled(root, qsdict)
    #set query string defaults
    file = ''
    showallfiles = 'false'
    #override with query string values
    if qsdict.has_key('file'):
        file= '/%s' % qsdict['file']
    if qsdict.has_key('showallfiles'):
        showallfiles = '%s' % qsdict['showallfiles']
    #start generation of document
    thePage.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html14/loose.dtd">')
    thePage.append('<html>')
    #generate document head
    thePage.append('<head>')
    thePage.append('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">')
    thePage.append('<meta http-equiv="pragma" content="no-cache">')
    thePage.append('<meta http-equiv="cache-control" content="no-cache">')
    thePage.append('<link rel="stylesheet" href="/public/styles/navigation.css" type="text/css">')
    thePage.append('<script language="JavaScript1.3" type="text/javascript" src="/webapi/js/sdk2.js"></script>')
    thePage.append('<script src="/webapi/js/webexpress.js" type="text/javascript"></script>')
    thePage.append('<!-- Widget files -->')
    thePage.append('<script language="JavaScript1.3" type="text/javascript" src="/webapi/js/widget.js"></script>')
    #add script to include all widgets
    thePage.extend(rzutils.genWidgetScript(root))
    thePage.append(addDynamicEditPane())
    thePage.append('</head>')
    # generate document body
    thePage.append('<body class="kubrick tundra">')
    thePage.append('<div id="background"><img src="/public/images/pageBackground.jpg" /></div>')
    thePage.append('<h1 class="title">Network Building Mediator</h1>')
    thePage.append('<ul class="actions">')
    thePage.append('<li><a href="">About</a></li>')
    thePage.append('<li><a id="logout" href="/logout"> Logout </a></li>')
    thePage.append('</ul>')
    thePage.append('</div>')
    thePage.append("""
        <div id="primary-tabs"
            title=""
            class="primary-tabs"
            href="/public/templates/primary.html"
            extractContent="false"
            preventCache="false"
            dojoType="dijit.layout.ContentPane"
            onDownloadEnd="dojo.addClass('webexpress-tab-button', 'selected');" 
            addOnUnload=WebExpress_ConfirmExit;>
        </div>""")
    thePage.append('<div id="stage">')
    thePage.append('<div class="pane" id="navigation-pane">')

    thePage.append('<div>')
    thePage.append('<div class="navigation-menu">')
    thePage.append('<ul class="button-menu">')
    thePage.append('<li class="button">')
    thePage.append('<a href="javascript:WebExpress_FileOpsNew()">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('Create New File')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append('<li class="button">')
    thePage.append('<a href="javascript:WebExpress_FileOpsView()">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('View Selected File')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append('<li class="button">')
    thePage.append('<a href="javascript:WebExpress_FileOpsEdit()">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('Edit Selected File')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append('<li class="button">')
    thePage.append('<a href="javascript:WebExpress_FileOpsDelete()">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('Delete Selected File')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append('<li class="button">')
    thePage.append('<a href="javascript:WebExpress_FileOpsCopyMultiple()">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('Copy Multiple Files')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append('<li class="button">')
    thePage.append('<a href="javascript:WebExpress_FileOpsDeleteMultiple()">')
    thePage.append('<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('Delete Multiple Files')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append( '<li class="button">')
    thePage.append('<a href="fileupload.html">')
    thePage.append( '<img class="prefix" src="/public/images/transparent.png" />')
    thePage.append('Upload A File')
    thePage.append('<img class="suffix" src="/public/images/transparent.png" />')
    thePage.append('</a>')
    thePage.append('</li>')
    thePage.append('</ul>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('<div id="contentarea" class="pane"  align="center" >')
    thePage.append('<table style="margin-top: 75px;">')
    thePage.append('    <tr valign="baseline">')
    thePage.append('        <td>WebExpress allows you to make customized web pages, with real-time data, that get served up by the Cisco Network Building Mediator.</td>')
    thePage.append('        <td>&nbsp;&nbsp;')
    #add script for file selector
    thePage.extend(rzutils.genFileSelectorScript(root,'*.htm;*.html',showallfiles))
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('<script type="text/javascript">')
    thePage.append('function WebExpress_FileOpsEdit(){')
    thePage.append('var f = document.getElementById("theFile").value;')
    thePage.append('top.location = "/omega/webexpress/webexpress.psp?showallfiles=%s&file=" + f;' % (showallfiles))
    thePage.append('}')
    thePage.append('function WebExpress_FileOpsNew(){')
    thePage.append('top.location = "/omega/webexpress/webexpress.psp?showallfiles=%s&file=NEWFILE";' % (showallfiles))
    thePage.append('}')
    thePage.append('function WebExpress_FileOpsDeleteMultiple(){')
    thePage.append('top.location = "/omega/webexpress/deletemultiple.html?showallfiles=%s";' % (showallfiles))
    thePage.append('}')
    thePage.append('function WebExpress_FileOpsCopyMultiple(){')
    thePage.append('top.location = "/omega/webexpress/copymultiple.html?showallfiles=%s";' % (showallfiles))
    thePage.append('}')
    thePage.append('function WebExpress_ConfirmExit(){')
    thePage.append('alert("You have not saved the form yet. Are you sure ?");')
    thePage.append('}')
    thePage.append('</script>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</body>')
    thePage.append('</html>')
    return thePage

def makeSecondPageDisabled(root, qsdict):
    thePage = []
    #set query string defaults
    file = ''
    showallfiles = 'false'
    #override with query string values
    if qsdict.has_key('file'):
        file= '/%s' % qsdict['file']
    if qsdict.has_key('showallfiles'):
        showallfiles = '%s' % qsdict['showallfiles']

    #start generation of document
    thePage.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html14/loose.dtd">')
    thePage.append('<html>')
    #generate document head
    thePage.append('<head>')
    thePage.append('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">')
    thePage.append('<meta http-equiv="pragma" content="no-cache">')
    thePage.append('<meta http-equiv="cache-control" content="no-cache">')
    thePage.append('<link rel="stylesheet" href="/public/styles/page.css" type="text/css">')
    thePage.append('<script language="JavaScript1.3" type="text/javascript" src="/webapi/js/sdk2.js"></script>')
    thePage.append('<script src="/webapi/js/webexpress.js" type="text/javascript"></script>')
    thePage.append('<!-- Widget files -->')
    thePage.append('<script language="JavaScript1.3" type="text/javascript" src="/webapi/js/widget.js"></script>')
    #add script to include all widgets
    thePage.extend(rzutils.genWidgetScript(root))
    thePage.append(addDynamicEditPane())
    thePage.append('</head>')
    # generate document body
    thePage.append('<body class="kubrick tundra">')
    thePage.append('<div id="background"><img src="/public/images/pageBackground.jpg" /></div>')
    thePage.append('<h1 class="title">Network Building Mediator</h1>')
    thePage.append('<ul class="actions">')
    thePage.append('<li><a href="">About</a></li>')
    thePage.append('<li><a id="logout" href="/logout"> Logout </a></li>')
    thePage.append('</ul>')
    thePage.append('</div>')
    thePage.append("""
        <div id="primary-tabs"
            title=""
            class="primary-tabs"
            href="/public/templates/primary.html"
            extractContent="false"
            preventCache="false"
            dojoType="dijit.layout.ContentPane"
            onDownloadEnd="dojo.addClass('webexpress-tab-button', 'selected');" >
        </div>""")
    thePage.append('<div id="stage">')
    thePage.append('<div class="pane" id="navigation-pane">')
    thePage.append('<div>')
    thePage.append('<div class="navigation-menu">')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('<div id="contentarea" class="pane" valign="center">')
    thePage.append('<table cellspacing="0" cellpadding="0" border="0"  width="938" height="30">')
    thePage.append('<tr>')
    thePage.append('<td></td>')
    thePage.append('<td valign="top">')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table border="0" cellspacing="0" cellpadding="0">')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table border="0" bgcolor="white" cellpadding="0" cellspacing="0">')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('</td><td bgcolor="#33a0cd" class="white">&nbsp;&nbsp;&nbsp;MESSAGES&nbsp;</td>')
    thePage.append('<td>')
    thePage.append('<table cellpadding="0"  width="250" height="25" border="0">')
    thePage.append('<tr>')
    thePage.append('<td style="text-align:left;vertical-align:top" class="smalltext" id="msg">&nbsp;</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('<td align="center">')
    thePage.append('<table>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table>')
    thePage.append('<tr>')

    thePage.append('<td><a href="javascript:WebExpress_SaveFileWin();"><img src="/webapi/images/button_saveFile2.png" width="91" height="29" alt="" border="0"></a></td>')
    thePage.append('<td><a href="javascript:WebExpress_LaunchHelp();">'
                   '<img src="/webapi/images/button_help2.png" width="91" height="29"alt="" border="0">'
                   '</a></td>')
    thePage.append('<td><a href="/omega/webexpress/index.html">'
                   '<img src="/webapi/images/button_back2.png" width="91" height="29" alt="" border="0">'
                   '</a></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('<br>')
    thePage.append('<table cellspacing="0" cellpadding="0" border="0">')
    thePage.append('<tr>')
    thePage.append('<td valign="top" align="center">')
    thePage.append('<table  width="150" border="0" cellspacing="0" cellpadding="0" >')
    thePage.append('<tr>')
    thePage.append('<td nowrap><img src="/webapi/images/spacer.gif" width="1" height="20" alt="" border="0">&nbsp;&nbsp;Add or Delete Widgets:</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td nowrap><img src="/webapi/images/spacer.gif" width="1" height="10" alt="" border="0">&nbsp;</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td colspan="4" valign="bottom" align="center">')
    thePage.append('<select name="WebExpressWidgets" class="webexpressselect" id="WebExpressWidgets" disabled>')
    thePage.append('<option value="" SELECTED>Please select a widget</option>')
    thePage.append('</select></td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td><img src="/webapi/images/spacer.gif" width="1" height="10" alt="" border="0">&nbsp;</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table cellspacing="1" cellpadding="1" border="0" align="center">')
    thePage.append('<tr>')
    thePage.append('<td rowspan="2"><img src="/webapi/images/button_create2.png" width="65" height="28" alt="" border="0" style="cursor:pointer; padding:0px 6px;" onclick="WebExpress_CreateWidget()"></td>')
    thePage.append('<td rowspan="2"><img src="/webapi/images/button_copy2.png" width="65" height="28" alt="" border="0"  onclick="WebExpress_CopyWidget()"></td>')
    thePage.append('<td rowspan="2"><img src="/webapi/images/button_delete2.png" width="65" height="28" alt="" border="0" onclick="WebExpress_DeleteWidget()"></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td nowrap><img src="/webapi/images/spacer.gif" width="1" height="30" alt="" border="0">&nbsp;&nbsp;Selected Widget:</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td class="smalltext" valign="top">&nbsp;&nbsp;&nbsp;&nbsp;Type:&nbsp;<span class="smalltext" id="widget_type">&nbsp;</span></td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td class="smalltext" valign="top">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ID:&nbsp;<span class="smalltext" id="widget_id">&nbsp;</span></td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td nowrap><img src="/webapi/images/spacer.gif" width="1" height="30" alt="" border="0">&nbsp;&nbsp;Position Widget:</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table>')
    thePage.append('<tr>')
    thePage.append('<td width="70%" align="right" class="smalltext" valign="top">Z-Index:</td>')
    thePage.append('<td width="30%"><input type="text" id="zaxis" size="3"></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table>')
    thePage.append('<tr>')
    thePage.append('<td  width="70%" align="right" class="smalltext" valign="top">X Coordinate:</td>')
    thePage.append('<td width="30%"><input type="text" id="xaxis" size="3"></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table>')
    thePage.append('<tr>')
    thePage.append('<td  width="70%" align="right" class="smalltext" valign="top">Y Coordinate:</td>')
    thePage.append('<td width="30%" ><input type="text" id="yaxis" size="3"></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td>')
    thePage.append('<table>')
    thePage.append('<tr>')
    thePage.append('<td nowrap><img src="/webapi/images/spacer.gif" width="1" height="30" alt="" border="0">&nbsp;&nbsp;Configure Page:</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td width="50%" align="right" class="smalltext" valign="top">&nbsp;&nbsp;&nbsp;Refresh Page:</td>')
    thePage.append('<td width="50%" ><input type="text" id="pagerefresh" size="9" readonly></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('<tr>')
    thePage.append('<td align="center" valign="top"><img src="/webapi/images/spacer.gif" width="1" height="40" alt="" border="0"><img src="/webapi/images/button_configure2.png" width="91" height="29" alt="" border="0"  onclick="WebExpress_ConfigurePage()"></td>')
    thePage.append('</tr>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td bgcolor="#97B1D0"><a href="/index.html"></a></td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td align="center" valign="top" bgcolor="#97B1D0"></td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('<td>&nbsp;</td>')
    thePage.append('<td id="editFrameHolder" colspan="3" width="730" valign="top" border="0" editFile="%s"></td>' % (file))
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</div>')
    # Force bgcolor so FF acts like IE.  I don't know which one is actually right.
    thePage.append('<script type="text/javascript">')
    thePage.append('WebExpress_start();')
    thePage.append('</script>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</body>')
    thePage.append('</html>')
    return thePage

def makePage(root, qsdict):
    #if access to application is allowed, generate enabled pages
    if rzutils.isApplicationAllowed('webexpress'):
        #check for file in query string arguments
        if qsdict.has_key('file'):
            thePage = makeSecondPageEnabled(root, qsdict)
        else:
            thePage = makeFirstPageEnabled(root, qsdict)
    #else generate disabled pages
    else:
        #check for file in query string arguments
        if qsdict.has_key('file'):
            thePage = makeSecondPageDisabled(root, qsdict)
        else:
            thePage = makeFirstPageDisabled(root, qsdict)
    return thePage

def makeDeleteMultipleEnabled(root, qsdict):
    thePage = []
    #extra check to prevent user calling this function directly
    if not rzutils.isApplicationAllowed('webexpress'):
        return makeDeleteMultipleDisabled(root, qsdict)
    #set query string defaults
    file = ''
    showallfiles = 'false'
    #override with query string values
    if qsdict.has_key('file'):
        file= '/%s' % qsdict['file']
    if qsdict.has_key('showallfiles'):
        showallfiles = '%s' % qsdict['showallfiles']

    #start generation of document
    thePage.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html14/loose.dtd">')
    thePage.append('<html>')
    #generate document head
    thePage.append('<head>')
    thePage.append('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">')
    thePage.append('<link rel="stylesheet" href="/public/styles/page.css" type="text/css">')
    thePage.append('<script language="JavaScript1.3" type="text/javascript" src="/webapi/js/sdk2.js"></script>')
    thePage.append('<script src="/webapi/js/webexpress.js" type="text/javascript"></script>')
    #add script to include all widgets

    thePage.append(addDynamicEditPane())
    thePage.append('</head>')
    # generate document body
    thePage.append('<body class="kubrick tundra">')
    thePage.append('<div id="background"><img src="/public/images/pageBackground.jpg" /></div>')
    thePage.append('<h1 class="title">Network Building Mediator</h1>')
    thePage.append('<ul class="actions">')
    thePage.append('<li><a href="">About</a></li>')
    thePage.append('<li><a id="logout" href="/logout"> Logout </a></li>')
    thePage.append('</ul>')
    thePage.append('</div>')
    thePage.append("""
        <div id="primary-tabs"
            title=""
            class="primary-tabs"
            href="/public/templates/primary.html"
            extractContent="false"
            preventCache="false"
            dojoType="dijit.layout.ContentPane"
            onDownloadEnd="dojo.addClass('webexpress-tab-button', 'selected');" >
        </div>""")
    thePage.append('<div id="stage">')
    thePage.append('<div class="pane" id="navigation-pane">')
    thePage.append('<div>')
    thePage.append('<div class="navigation-menu">')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('<div id="contentarea" class="pane"  >')
    thePage.append('<table  border="0" cellpadding="0" cellspacing="0" width="100%" align="center" >')
    thePage.append('<tr>')
    thePage.append('<td valign="top" align="center" >Use shift+click to select a contiguous range, ctrl+click to select multiple items.')
    thePage.append('<div class="line-dotted"><img border="0" src="../media/images/pxl.gif" width="1" height="1" alt=""></div>')
    thePage.append('<table border="0" cellpadding="0" cellspacing="0" width="100%" align="center" >')
    thePage.append('<tr>')
    thePage.append('<td width="100%" valign="top" align="center" >')
    thePage.append('<span class="header">Delete multiple files</span><br>Select files for deletion:<br><br>')
    #add script for file selector
    thePage.extend(rzutils.genFileSelectorScriptMultiple(root,'*.htm;*.html',showallfiles))
    thePage.append('<a href="javascript:WebExpress_DeleteMultipleStart()"><img src="../media/images/btn_delete.png" width="180" height="22" alt="" border="0"></a>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('<td>')
    thePage.append('<img src="../media/images/pxl.gif" width="20" height="1" alt="">')
    thePage.append('</td>')
    thePage.append('<td valign="top">')
    thePage.append('<img src="../media/images/pxl.gif" width="167" height="167" alt="" vspace="0">')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('<script type="text/javascript">')
    thePage.append('var WebExpress_DeleteMultipleTimeout = 200;')
    thePage.append('var WebExpress_DeleteMultipleCurrentIndex = 0;')
    thePage.append('var WebExpress_DeleteMultipleNumOpts = 0;')
    thePage.append('var WebExpress_DeleteMultipleDoConfirm = 1;')
    thePage.append('var WebExpress_DeleteMultipleSelector = null;')
    thePage.append('function WebExpress_OpenDeleteConfirm(filename){')
    thePage.append('var result = window.showModalDialog("delmultdialog.html", filename, "dialogHeight:200px; dialogWidth:300px; center:yes; help:no; status:no");')
    thePage.append('return result;')
    thePage.append('}')
    thePage.append('function WebExpress_DoDeleteMultiple(filename){')
    thePage.append('WebExpress_FileOpsDeleteMultiple(filename);')
    thePage.append('setTimeout("WebExpress_DeleteMultipleLoop()", WebExpress_DeleteMultipleTimeout);')
    thePage.append('}')
    thePage.append('function WebExpress_DeleteMultipleStart(){')
    thePage.append('WebExpress_DeleteMultipleCurrentIndex = 0;')
    thePage.append('WebExpress_DeleteMultipleDoConfirm = 1;')
    thePage.append('WebExpress_DeleteMultipleSelector = document.getElementById("theFile");')
    thePage.append('WebExpress_DeleteMultipleNumOpts = WebExpress_DeleteMultipleSelector.options.length;')
    thePage.append('WebExpress_DeleteMultipleLoop();')
    thePage.append('}')
    thePage.append('function WebExpress_DeleteMultipleLoop(){')
    thePage.append('if(WebExpress_DeleteMultipleCurrentIndex < WebExpress_DeleteMultipleNumOpts) {')
    thePage.append('if(WebExpress_DeleteMultipleSelector.options[WebExpress_DeleteMultipleCurrentIndex].selected == true) {')
    thePage.append('if(WebExpress_DeleteMultipleDoConfirm) {')
    thePage.append('var result = WebExpress_OpenDeleteConfirm(WebExpress_DeleteMultipleSelector.options[WebExpress_DeleteMultipleCurrentIndex].text);')
    thePage.append('}')
    thePage.append('if(!WebExpress_DeleteMultipleDoConfirm || result == "yes") {')
    thePage.append('var myFile = WebExpress_DeleteMultipleSelector.options[WebExpress_DeleteMultipleCurrentIndex].value;')
    thePage.append('WebExpress_DeleteMultipleCurrentIndex++;')
    thePage.append('WebExpress_DoDeleteMultiple(myFile);')
    thePage.append('} // if no confirm or yes to confirm')
    thePage.append('else if(result == "yestoall") {')
    thePage.append('WebExpress_DeleteMultipleDoConfirm = 0;')
    thePage.append('var myFile = WebExpress_DeleteMultipleSelector.options[WebExpress_DeleteMultipleCurrentIndex].value;')
    thePage.append('WebExpress_DeleteMultipleCurrentIndex++;')
    thePage.append('WebExpress_DoDeleteMultiple(myFile);')
    thePage.append('}')
    thePage.append('else if(result == "no") {')
    thePage.append('//skip this file')
    thePage.append('WebExpress_DeleteMultipleCurrentIndex++;')
    thePage.append('setTimeout("WebExpress_DeleteMultipleLoop()",0);')
    thePage.append('}')
    thePage.append('else {')
    thePage.append('//abort')
    thePage.append('top.location.reload(true);')
    thePage.append('}')
    thePage.append('} // if option is selected')
    thePage.append('else {')
    thePage.append('WebExpress_DeleteMultipleCurrentIndex++;')
    thePage.append('setTimeout("WebExpress_DeleteMultipleLoop()",0);')
    thePage.append('}')
    thePage.append('} // if CurrentIndex < NumOpts')
    thePage.append('else {')
    thePage.append('setTimeout("top.location.reload(true);", 100); // normal completion')
    thePage.append('}')
    thePage.append('}')
    thePage.append('</script>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</body>')
    thePage.append('</html>')
    return thePage

def makeDeleteMultipleDisabled(root, qsdict):
    thePage = []
    #set query string defaults
    file = ''
    showallfiles = 'false'
    #override with query string values
    if qsdict.has_key('file'):
        file= '/%s' % qsdict['file']
    if qsdict.has_key('showallfiles'):
        showallfiles = '%s' % qsdict['showallfiles']

    #start generation of document
    thePage.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">')
    thePage.append('<html>')
    #generate document head
    thePage.append('<head>')
    thePage.append('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">')
    thePage.append('<link rel="stylesheet" href="/public/styles/page.css" type="text/css">')
    thePage.append('<script language="JavaScript1.3" type="text/javascript" src="/webapi/js/sdk2.js"></script>')
    thePage.append('<script src="/webapi/js/webexpress.js" type="text/javascript"></script>')
    thePage.append(addDynamicEditPane())
    thePage.append('</head>')
    # generate document body
    thePage.append('<body class="kubrick tundra">')
    thePage.append('<div id="background"><img src="/public/images/pageBackground.jpg" /></div>')
    thePage.append('<h1 class="title">Network Building Mediator</h1>')
    thePage.append('<ul class="actions">')
    thePage.append('<li><a href="">About</a></li>')
    thePage.append('<li><a id="logout" href="/logout"> Logout </a></li>')
    thePage.append('</ul>')
    thePage.append('</div>')
    thePage.append("""
        <div id="primary-tabs"
            title=""
            class="primary-tabs"
            href="/public/templates/primary.html"
            extractContent="false"
            preventCache="false"
            dojoType="dijit.layout.ContentPane"
            onDownloadEnd="dojo.addClass('webexpress-tab-button', 'selected');" >
        </div>""")
    thePage.append('<div id="stage">')
    thePage.append('<div class="pane" id="navigation-pane">')
    thePage.append('<div>')
    thePage.append('<div class="navigation-menu">')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('<div id="contentarea" class="pane"  >')
    thePage.append('<table  border="0" cellpadding="0" cellspacing="0" width="100%" align="center"  >')
    thePage.append('<tr>')
    thePage.append('<td valign="top" align="center" >Use shift+click to select a contiguous range, ctrl+click to select multiple items.')
    thePage.append('<div class="line-dotted"><img border="0" src="../media/images/pxl.gif" width="1" height="1" alt=""></div>')
    thePage.append('<table border="0" cellpadding="0" cellspacing="0" width="100%" align="center" >')
    thePage.append('<tr>')
    thePage.append('<td width="100%" valign="top" align="center" >')
    thePage.append('<span class="header">Delete multiple files</span><br>Select files for deletion:<br><br>')
    #add script for file selector
    thePage.extend(rzutils.genFileSelectorScriptMultiple(root,'*.htm;*.html',showallfiles))
    thePage.append('<a href="javascript:WebExpress_FileOpsDisabled()"><img src="../media/images/btn_delete.png" width="180" height="20" alt="" border="0"></a>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('<td>')
    thePage.append('<img src="../media/images/pxl.gif" width="20" height="1" alt="">')
    thePage.append('</td>')
    thePage.append('<td valign="top">')
    thePage.append('<img src="../media/images/pxl.gif" width="167" height="167" alt="" vspace="0">')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('<script type="text/javascript">')
    thePage.append('function WebExpress_FileOpsDisabled(){')
    thePage.append('alert("This feature is disabled in this Omega version. Please contact your vendor for upgrade information.");')
    thePage.append('}')
    thePage.append('</script>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</body>')
    thePage.append('</html>')
    return thePage

def makeDeleteMultiple(root, qsdict):
    #if access to application is allowed, generate enabled page
    if rzutils.isApplicationAllowed('webexpress'):
        return makeDeleteMultipleEnabled(root, qsdict)
    #else generate disabled page
    else:
        return makeDeleteMultipleDisabled(root, qsdict)

def makeCopyMultipleEnabled(root, qsdict):
    thePage = []
    #extra check to prevent user calling this function directly
    if not rzutils.isApplicationAllowed('webexpress'):
        return makeDeleteMultipleDisabled(root, qsdict)
    #set query string defaults
    file = ''
    showallfiles = 'false'
    #override with query string values
    if qsdict.has_key('file'):
        file= '/%s' % qsdict['file']
    if qsdict.has_key('showallfiles'):
        showallfiles = '%s' % qsdict['showallfiles']

    #start generation of document
    thePage.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html14/loose.dtd">')
    thePage.append('<html>')
    #generate document head
    thePage.append('<head>')
    thePage.append('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">')
    thePage.append('<link rel="stylesheet" href="/public/styles/page.css" type="text/css">')
    thePage.append('<script language="JavaScript1.3" type="text/javascript" src="/webapi/js/sdk2.js"></script>')
    thePage.append('<script src="/webapi/js/webexpress.js" type="text/javascript"></script>')

    thePage.append('<script type="text/javascript">')
    thePage.append('function focusElement(formName, elemName){')
    thePage.append('var elem = document.forms[formName].elements[elemName];')
    thePage.append('elem.focus();')
    thePage.append('elem.select();')
    thePage.append('}')
    thePage.append('function updateFileBaseName(){')
    thePage.append('var fileselector = document.getElementById("theFile");')
    thePage.append('var fileindex = fileselector.selectedIndex;')
    thePage.append('var basename = fileselector.options[fileindex].value;')
    thePage.append('var basenamelower = basename.toLowerCase();')
    thePage.append('var extIndex = basenamelower.lastIndexOf(".htm")')
    thePage.append('document.getElementById("filebasename").value = basename.slice(0,extIndex) + "~" + basename.slice(extIndex);')
    thePage.append('}')
    thePage.append('function isCopiesValid(elem){')
    thePage.append('var mynum = parseInt(elem.value);')
    thePage.append('if(isNaN(mynum)){')
    thePage.append('alert("Number of Copies must be between 1 and 999!");')
    thePage.append('''setTimeout("focusElement('" + elem.form.name + "', '" + elem.name + "')", 0);''')
    thePage.append('return false;')
    thePage.append('}')
    thePage.append('if(mynum < 1 || mynum > 999){')
    thePage.append('alert("Number of Copies must be between 1 and 999!");')
    thePage.append('''setTimeout("focusElement('" + elem.form.name + "', '" + elem.name + "')", 0);''')
    thePage.append('return false;')
    thePage.append('}')
    thePage.append('return true;')
    thePage.append('}')
    thePage.append('function isBaseNameValid(elem){')
    thePage.append('var re1 = /^omega\//;')
    thePage.append('var re2 = /^webapi\//;')
    thePage.append('var re3 = /^(\S+\/)*(\S+)\.((htm)|(html))$/;')
    thePage.append('var basenamestr = elem.value;')
    thePage.append('if(basenamestr.length < 5){')
    thePage.append('alert("Please select file from selector or enter text to populate file base name!");')
    thePage.append('''setTimeout("focusElement('" + elem.form.name + "', '" + elem.name + "')", 0);''')
    thePage.append('return false;')
    thePage.append('}')
    thePage.append('if(basenamestr.match(re1)){')
    thePage.append('alert("Illegal directory!");')
    thePage.append('''setTimeout("focusElement('" + elem.form.name + "', '" + elem.name + "')", 0);''')
    thePage.append('return false;')
    thePage.append('}')
    thePage.append('if(basenamestr.match(re2)){')
    thePage.append('alert("Illegal directory!");')
    thePage.append('''setTimeout("focusElement('" + elem.form.name + "', '" + elem.name + "')", 0);''')
    thePage.append('return false;')
    thePage.append('}')
    thePage.append('if(basenamestr.indexOf("~") == -1){')
    thePage.append('''alert('File base name must contain at least one "~"!');''')
    thePage.append('''setTimeout("focusElement('" + elem.form.name + "', '" + elem.name + "')", 0);''')
    thePage.append('return false;')
    thePage.append('}')
    thePage.append('if(basenamestr.indexOf("/") == 0){')
    thePage.append('''alert('File base name must not start with "/"!');''')
    thePage.append('''setTimeout("focusElement('" + elem.form.name + "', '" + elem.name + "')", 0);''')
    thePage.append('return false;')
    thePage.append('}')
    thePage.append('if(basenamestr.toLowerCase().match(re3)){')
    thePage.append('return true;')
    thePage.append('}')
    thePage.append('alert("Bad base file name!");')
    thePage.append('''setTimeout("focusElement('" + elem.form.name + "', '" + elem.name + "')", 0);''')
    thePage.append('return false;')
    thePage.append('}')
    thePage.append('function validateCopyMultiple(form){')
    thePage.append('if(isCopiesValid(form.copies)){')
    thePage.append('if(isBaseNameValid(form.filebasename)){')
    thePage.append('return true;')
    thePage.append('}')
    thePage.append('}')
    thePage.append('return false;')
    thePage.append('}')
    thePage.append('</script>')
    thePage.append(addDynamicEditPane())
    thePage.append('</head>')
    # generate document body
    thePage.append('<body class="kubrick tundra">')
    thePage.append('<div id="background"><img src="/public/images/pageBackground.jpg" /></div>')
    thePage.append('<h1 class="title">Network Building Mediator</h1>')
    thePage.append('<ul class="actions">')
    thePage.append('<li><a href="">About</a></li>')
    thePage.append('<li><a id="logout" href="/logout"> Logout </a></li>')
    thePage.append('</ul>')
    thePage.append('</div>')
    thePage.append("""
        <div id="primary-tabs"
            title=""
            class="primary-tabs"
            href="/public/templates/primary.html"
            extractContent="false"
            preventCache="false"
            dojoType="dijit.layout.ContentPane"
            onDownloadEnd="dojo.addClass('webexpress-tab-button', 'selected');" >
        </div>""")
    thePage.append('<div id="stage">')
    thePage.append('<div class="pane" id="navigation-pane">')
    thePage.append('<div>')
    thePage.append('<div class="navigation-menu">')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('<div id="contentarea" class="pane" vAlign="center" align="center" width="100% >')
    thePage.append('<table  border="0" cellpadding="0" cellspacing="0" align="center" width="100%" >')
    thePage.append('<tr>')
    thePage.append('<td valign="top">Create copies of template file with copy number appended (i.e, 1 to number of copies).  Use "~" in template file base name and widget node paths for number substitution during copy.')
    thePage.append('<form action="/omega/webexpress/docopymultiple.psp" method="post" enctype="multipart/form-data" name="docopymultiple" onsubmit="return validateCopyMultiple(this)" align="center">')
    thePage.append('<table border="0" cellpadding="0" cellspacing="0" width="100%" align="center">')
    thePage.append('<tr>')
    thePage.append('<td width="100%" valign="top" align="center">')
    thePage.append('<span class="header">Copy multiple files</span><br>Select template file for copy:<br>')
    #add script for file selector
    thePage.extend(rzutils.genCopyMultipleSelectorScript(root,'*.htm;*.html',showallfiles, 'updateFileBaseName()'))
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td width="100%" valign="top">')
    thePage.append('Number of Copies:<br><input type="text" id="copies" name="copies" size="4" maxlength="3" value="1">')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td width="100%" valign="top">')
    thePage.append('File Base Name:<br><input type="text" id="filebasename" name="filebasename" size="60" maxlength="60" value="">')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td width="100%" valign="top">')
    thePage.append('<br>')
    thePage.append('<input type="image" id="submitCopyMultiple" src="../media/images/btn_copy.png" width="180" height="22" alt="" border="0">')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</form>')
    thePage.append('</td>')
    thePage.append('<td>')
    thePage.append('<img src="../media/images/pxl.gif" width="20" height="1" alt="">')
    thePage.append('</td>')
    thePage.append('<td valign="top">')
    thePage.append('<img src="../media/images/pxl.gif" width="167" height="167" alt="" vspace="0">')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('<script type="text/javascript">')
    thePage.append('document.getElementById("theFile").selectedIndex = -1;')
    thePage.append('</script>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</body>')
    thePage.append('</html>')
    return thePage

def makeCopyMultipleDisabled(root, qsdict):
    thePage = []
    #set query string defaults
    file = ''
    showallfiles = 'false'
    #override with query string values
    if qsdict.has_key('file'):
        file= '/%s' % qsdict['file']
    if qsdict.has_key('showallfiles'):
        showallfiles = '%s' % qsdict['showallfiles']

    #start generation of document
    thePage.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">')
    thePage.append('<html>')
    #generate document head
    thePage.append('<head>')
    thePage.append('<!-- Copyright (c) 2004 Envenergy')
    thePage.append('Cisco Network Building Mediator &copy; 2005-2011')
    thePage.append('Purpose: entry point to WebExpress editor')
    thePage.append('$Name: mediator_3_1_2_branch $')
    thePage.append('$Id: genwebexpress.py 20606 2011-06-22 10:50:27Z jchaudhu $ -->')
    thePage.append('<title>Web Express</title>')
    thePage.append('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">')

    thePage.append('<script language="JavaScript1.3" type="text/javascript" src="/webapi/js/sdk2.js"></script>')
    thePage.append('<script src="/webapi/js/webexpress.js" type="text/javascript"></script>')

    thePage.append('<script type="text/javascript">')
    thePage.append('function updateFileBaseName(){')
    thePage.append('var fileselector = document.getElementById("theFile");')
    thePage.append('var fileindex = fileselector.selectedIndex;')
    thePage.append('document.getElementById("filebasename").value = fileselector.options[fileindex].value;')
    thePage.append('}')
    thePage.append('</script>')
    thePage.append(addDynamicEditPane())
    thePage.append('</head>')
    # generate document body
    thePage.append('<body class="kubrick tundra">')
    thePage.append('<table  border="0" cellpadding="0" cellspacing="0" align="center" width="100% >')
    thePage.append('<tr>')
    thePage.append('<td valign="top">Create copies of template file with copy number appended (i.e, 1 to number of copies).  Use "~" in template file base name and widget node paths for number substitution during copy.')
    thePage.append('<table border="0" cellpadding="0" cellspacing="0" width="100%" align="center">')
    thePage.append('<tr>')
    thePage.append('<td width="100%" valign="top" align="center">')
    thePage.append('<span class="header">Copy multiple files</span><br>Select template file for copy:<br><br>')
    #add script for file selector
    thePage.extend(rzutils.genCopyMultipleSelectorScript(root,'*.htm;*.html',showallfiles, 'updateFileBaseName()'))
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td width="100%" valign="top">')
    thePage.append('Number of Copies:<br><br><input type="text" id="copies" name="copies" size="4" maxlength="3" value="1">')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('<tr>')
    thePage.append('<td width="100%" valign="top">')
    thePage.append('<br><br>')
    thePage.append('<a href="javascript:WebExpress_FileOpsDisabled()"><img src="../media/images/btn_copy.png" width="180" height="22" alt="" border="0"></a>')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('</td>')
    thePage.append('<td>')
    thePage.append('<img src="../media/images/pxl.gif" width="20" height="1" alt="">')
    thePage.append('</td>')
    thePage.append('<td valign="top">')
    thePage.append('<img src="../media/images/pxl.gif" width="167" height="167" alt="" vspace="0">')
    thePage.append('</td>')
    thePage.append('</tr>')
    thePage.append('</table>')
    thePage.append('<script type="text/javascript">')
    thePage.append('function WebExpress_FileOpsDisabled(){')
    thePage.append('alert("This feature is disabled in this Omega version. Please contact your vendor for upgrade information.");')
    thePage.append('}')
    thePage.append('document.getElementById("theFile").selectedIndex = -1;')
    thePage.append('</script>')
    thePage.append('</div>')
    thePage.append('</div>')
    thePage.append('</body>')
    thePage.append('</html>')
    return thePage

def makeCopyMultiple(root, qsdict):
    #if access to application is allowed, generate enabled page
    if rzutils.isApplicationAllowed('webexpress'):
        return makeCopyMultipleEnabled(root, qsdict)
    #else generate disabled page
    else:
        return makeCopyMultipleDisabled(root, qsdict)
