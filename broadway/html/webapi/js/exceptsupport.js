/*
Copyright (C) 2008 2011 Cisco Systems

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
/* exceptsupport.js -- exception table support for WebScheduler
 * $Name: mediator_3_1_2_branch $
 * $Id: exceptsupport.js 20101 2011-03-06 16:02:15Z bhagn $
 */
var ExceptTableDebug = false;
var rowCount = 0;
var selectCellActive = false;
var currentCellSelection = null;

var myExceptions = null;

//schedule indices
var SCHEDULESNAME = 0;
var SCHEDULESDATA = 1;
var SCHEDULEDAYS = 0;
var SCHEDULEWEEKLY = 1;
var SCHEDULEEXCEPTIONS = 2;
var SCHEDULEDEFAULT = 3;
var DAYSNAME = 0;
var DAYSENTRYNAME = 0;
var DAYSENTRYTIME = 1;
var DAYSENTRYVALUE = 2;
var EXCEPTIONSNAME = 0;
var EXCEPTIONSENTRYNAME = 0;
var EXCEPTIONSENTRYSTART = 1;
var EXCEPTIONSENTRYEND = 2;
var EXCEPTIONSENTRYDAYSNAME = 3;

function ExceptTable_log(msg) {
  if(ExceptTableDebug) {
    try {
      if(parent.opener && parent.opener.SchedTable_log){
        parent.opener.SchedTable_log(msg);
      }
      else if(window.opener && window.opener.msglog != null){
        window.opener.msglog(msg);
      }
      else if(window.msglog){
        msglog(msg);
      }
    }
    catch(ex) {}
  }
}

function clearCellBackgrounds() {
  var editBody = document.getElementsByTagName('body')[0];
  var excepttable = GetElement(editBody,'table','excepttable');
  for (i=0;i<rowCount;i++){
    excepttable.rows[i].cells[0].setAttribute('bgColor','white');
  }
}

function CellMouseoverHandler(evt){
  //window.status = 'CellMouseoverHandler:';
  evt = (evt) ? evt : ((event) ? event : null);
  if(evt.stopPropagation)
    evt.stopPropagation();
  else
    evt.cancelBubble = true;
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var editBody = document.getElementsByTagName('body')[0];
  var excepttable = GetElement(editBody,'table','excepttable');
  if(!selectCellActive) {
    clearCellBackgrounds();
  }
  //elem.parentNode.parentNode.parentNode.setAttribute('bgColor','lightgrey');
  return true;
}

function CellMousemoveHandler(evt){
  //window.status = 'CellMousemoveHandler:';
  evt = (evt) ? evt : ((event) ? event : null);
  if(evt.stopPropagation)
    evt.stopPropagation();
  else
    evt.cancelBubble = true;
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myCell = elem.parentNode.parentNode.parentNode;
  if(!selectCellActive) {
    if(myCell.getAttribute('inUse') == 'true')
      myCell.setAttribute('bgColor','lightgrey');
  }
  return true;
}

function CellMouseoutHandler(evt){
  //window.status = 'CellMouseoutHandler:';
  evt = (evt) ? evt : ((event) ? event : null);
  /*if(evt.stopPropagation)
    evt.stopPropagation();
  else
    evt.cancelBubble = true;*/
  //var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var editBody = document.getElementsByTagName('body')[0];
  var excepttable = GetElement(editBody,'table','excepttable');
  if(!selectCellActive) {
    clearCellBackgrounds();
  }
  //elem.setAttribute('bgColor','white');
  return true;
}

function CellClickHandler(evt){
  //window.status = 'CellClickHandler:';
  evt = (evt) ? evt : ((event) ? event : null);
  if(evt.stopPropagation)
    evt.stopPropagation();
  else
    evt.cancelBubble = true;
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myCell = elem.parentNode.parentNode.parentNode;
  if(myCell.getAttribute('inUse') == 'true') {
    if(!selectCellActive) {
      selectCellActive = true;
      currentCellSelection = myCell;
      myCell.setAttribute('isSelected', 'true');
      myCell.setAttribute('bgColor','lightgrey');
    }
    else {
      if(currentCellSelection == myCell) {
        selectCellActive = false;
        currentCellSelection = null;
        myCell.setAttribute('isSelected', 'false');
        myCell.setAttribute('bgColor','white');
      }
      else {
        currentCellSelection.setAttribute('isSelected', 'false');
        currentCellSelection.setAttribute('bgColor','white');
        currentCellSelection = myCell;
        myCell.setAttribute('isSelected', 'true');
        myCell.setAttribute('bgColor','lightgrey');
      }
    }
  }
  return true;
}

function CellDblclickHandler(evt){
  //window.status = 'CellDblclickHandler:';
  return true;
}

function GetElement(element,t,element_name){
  var index;
  var e = null;
  var elements = element.getElementsByTagName(t);
  for (index=0;index<elements.length;index++){
    if (elements[index].getAttribute('element') &&
        elements[index].getAttribute('element') == element_name){ 
      e = elements[index];
      break;
    }
  }
  return e
}

function ExceptTableInit() {
  ExceptTable_log("ExceptTableInit entered");
  var excepttable = document.createElement('table');
  excepttable.setAttribute('element','excepttable');
  excepttable.setAttribute('cols', '1');
  excepttable.setAttribute('align','left');
  excepttable.setAttribute('cellpadding','0');
  excepttable.setAttribute('cellspacing','0');
  excepttable.setAttribute('width','100px');
  excepttable.setAttribute('frame','vsides');

  var editBody = document.getElementsByTagName('body')[0];
  editBody.appendChild(excepttable);
  //initialize (reinitialize) globals
  rowCount = 0;
  selectCellActive = false;
  currentCellSelection = null;
}

function addExceptTableRow(index) {
  ExceptTable_log("addExceptTableRow entered, index=" + index);
  var editBody = document.getElementsByTagName('body')[0];
  var excepttable = GetElement(editBody,'table','excepttable');
  excepttable.insertRow(index);
  excepttable.rows[index].insertCell(0);
  excepttable.rows[index].cells[0].align = 'center';
  excepttable.rows[index].cells[0].setAttribute('valign','middle');
  excepttable.rows[index].cells[0].setAttribute('width','64px');
  excepttable.rows[index].cells[0].setAttribute('height','20px');
  excepttable.rows[index].cells[0].setAttribute('inUse', 'false');
  excepttable.rows[index].cells[0].setAttribute('isSelected', 'false');
  rowCount++;
}

function deleteExceptTableRow(index) {
  var editBody = document.getElementsByTagName('body')[0];
  var excepttable = GetElement(editBody,'table','excepttable');
  excepttable.deleteRow(index);
  rowCount--;
}

function getNewDayCell(time,val) {
      var outercontainer = document.createElement('div');
      outercontainer.setAttribute('element','outercontainer');
      outercontainer.style.position = 'relative';
      outercontainer.style.verticalAlign = 'middle';
      outercontainer.style.height = 'auto';
      outercontainer.style.width = 'auto';
      outercontainer.style.textAlign = 'center'; //inherited by children
      outercontainer.style.fontSize = '9px';
      outercontainer.style.fontFamily = 'verdana, arial, san-serif';
      outercontainer.style.top = '0';
      outercontainer.style.left = '0';
      outercontainer.style.zIndex = '0';
  
	  var textcontainer = document.createElement('div');
      textcontainer.setAttribute('element','textcontainer');
      textcontainer.style.position = 'relative';
      textcontainer.style.verticalAlign = 'middle';
      textcontainer.style.height = 'auto';
      textcontainer.style.width = 'auto';
      textcontainer.style.backgroundColor = 'transparent';
      textcontainer.style.top = '0';
      textcontainer.style.left = '0';
      textcontainer.style.zIndex = '1';

      var placeholderdiv = document.createElement('div');
      placeholderdiv.setAttribute('element', 'placeholder');
      //placeholderdiv.style.position = 'absolute';
      placeholderdiv.style.verticalAlign = 'middle';
      placeholderdiv.style.backgroundColor = 'transparent';
      placeholderdiv.innerHTML = 'XXXXXXXXXX';
      placeholderdiv.style.top = '0';
      placeholderdiv.style.left = '0';
      placeholderdiv.style.zIndex = '1';
      placeholderdiv.style.visibility = 'hidden';
      textcontainer.appendChild(placeholderdiv);
  
      var nodedisplaydiv = document.createElement('div');
      nodedisplaydiv.setAttribute('element', 'nodedisplay');
      nodedisplaydiv.style.position = 'absolute';
      nodedisplaydiv.style.verticalAlign = 'middle';
      nodedisplaydiv.style.backgroundColor = 'transparent';
      nodedisplaydiv.style.borderWidth = '0px';
      nodedisplaydiv.style.borderStyle = 'none';
      //nodedisplaydiv.style.borderCollapse = 'collapse';
      //nodedisplaydiv.style.borderColor = 'red';
      //FIXTHIS: NN doesn't require offset to style.top
      nodedisplaydiv.style.top = '0'; // offset for placeholder border
      nodedisplaydiv.style.left = '0';
      nodedisplaydiv.style.zIndex = '2';
      nodedisplaydiv.innerHTML = time + " " + val;

      textcontainer.appendChild(nodedisplaydiv);

      var infodiv = document.createElement('div');
      infodiv.setAttribute('element','info');
      infodiv.setAttribute('type','hidden');  
      infodiv.setAttribute('time', time);  
      infodiv.setAttribute('setpoint', val);
      infodiv.setAttribute('dialog_enabled', 'true'); 
      infodiv.setAttribute('dialog_active', false); 
      //infodiv.style.position = 'relative';
      infodiv.style.backgroundColor = 'transparent';
      infodiv.style.top = '0';
      infodiv.style.left = '0';
      infodiv.style.height = '1';
      infodiv.style.width = '1';
      infodiv.style.zIndex = '0';
      infodiv.style.visibility = 'hidden';
      infodiv.style.display = 'none';
       
      outercontainer.appendChild(infodiv);
	  
      var hitareacontainer = document.createElement('div');
      hitareacontainer.setAttribute('element','hitareacontainer');
      var browserIE = new RegExp('internet explorer','gi');
      if(browserIE.test(navigator.appName)) {
        hitareacontainer.attachEvent('ondblclick',ExceptTableOpenChangeDayDialog);
        hitareacontainer.attachEvent('onclick',CellClickHandler);
        hitareacontainer.attachEvent('onmouseover',CellMouseoverHandler);
        hitareacontainer.attachEvent('onmouseout',CellMouseoutHandler);
        hitareacontainer.attachEvent('onmousemove',CellMousemoveHandler);
      }
      else {
        hitareacontainer.setAttribute('ondblclick','ExceptTableOpenChangeDayDialog(event)');
        hitareacontainer.setAttribute('onclick','CellClickHandler(event)');
        hitareacontainer.setAttribute('onmouseover','CellMouseoverHandler(event)');
        hitareacontainer.setAttribute('onmouseout','CellMouseoutHandler(event)');
        hitareacontainer.setAttribute('onmousemove','CellMousemoveHandler(event)');
      }
      hitareacontainer.style.position = 'absolute';
      hitareacontainer.style.verticalAlign = 'middle';
      hitareacontainer.style.height = 'auto';
      hitareacontainer.style.width = 'auto';
      hitareacontainer.style.height = 'auto';
      hitareacontainer.style.width = 'auto';
      hitareacontainer.style.margin = '0px';
      hitareacontainer.style.padding = '0px';
      hitareacontainer.style.border = '0px';
      if(window.parent && window.parent.WebExpressEditor) {  
  	    var mystring = "'url(" + window.parent.WebExpressProtocol + "//" + window.parent.WebExpressHostname + "/webapi/images/cleardot.gif)'";
      }
      else {
  	    var mystring = "'url(" + window.location.protocol + "//" + window.location.hostname + "/webapi/images/cleardot.gif)'";
      }
      /*var locstring = new String(window.location);
      var mystring = "'url(" + locstring.slice(0,locstring.lastIndexOf('/') + 1) + "cleardot.gif)'";*/
      hitareacontainer.style.backgroundImage = eval(mystring);
      hitareacontainer.style.backgroundRepeat = 'repeat';
      hitareacontainer.style.backgroundColor = 'transparent';
      hitareacontainer.style.top = '0';
      hitareacontainer.style.left = '0';
      hitareacontainer.style.zIndex = '3';

      var hitareadiv = document.createElement('div');
      hitareadiv.setAttribute('element', 'hitarea');
      //hitareadiv.style.position = 'absolute';
      hitareadiv.style.verticalAlign = 'middle';
      hitareadiv.style.backgroundColor = 'transparent';
      hitareadiv.innerHTML = 'XXXXXXXXXX';
      hitareadiv.style.top = '0';
      hitareadiv.style.left = '0';
      hitareadiv.style.zIndex = '0';
      hitareadiv.style.visibility = 'hidden';
      hitareacontainer.appendChild(hitareadiv);
	  
      textcontainer.appendChild(hitareacontainer);
      outercontainer.appendChild(textcontainer);
      return outercontainer;
}
 
function addExceptTableDayCell(time,val) {
  ExceptTable_log("addExceptTableDayCell,time=" + time + ",val=" + val);
  addExceptTableRow(rowCount);
  var editBody = document.getElementsByTagName('body')[0];
  var excepttable = GetElement(editBody,'table','excepttable');
  var myCell = getNewDayCell(time,val);
  excepttable.rows[rowCount - 1].cells[0].appendChild(myCell);
  excepttable.rows[rowCount - 1].cells[0].setAttribute('inUse', 'true');
}

function deleteExceptTableDayCell() {
  if(selectCellActive) {
    var myCell = GetElement(currentCellSelection,'div','outercontainer');
    currentCellSelection.removeChild(myCell);
    currentCellSelection.setAttribute('inUse', 'false');
    currentCellSelection.setAttribute('isSelected', 'false');
    currentCellSelection = null;
    selectCellActive = false;
    clearCellBackgrounds();
    ExceptTableCleanColumn();
    ExceptTablePruneRows();
    rowCount -= 1;
  }
}

function deleteExceptTableDayColumn() {
  ExceptTable_log("deleteExceptTableDayColumn() entered, rowCount=" + rowCount);
  if(selectCellActive) {
    currentCellSelection = null;
    selectCellActive = false;
  }
  var editBody = document.getElementsByTagName('body')[0];
  var excepttable = GetElement(editBody,'table','excepttable');
  for(var i=0;i < rowCount;i++) {
    var myContainer = GetElement(excepttable.rows[i].cells[0],'div','outercontainer');
    excepttable.rows[i].cells[0].removeChild(myContainer);
    excepttable.rows[i].cells[0].setAttribute('inUse', 'false');
    excepttable.rows[i].cells[0].setAttribute('isSelected', 'false');
  }
  ExceptTablePruneRows();
  rowCount = 0;
}

function ExceptTableCleanColumn() {
  ExceptTable_log("ExceptTableCleanColum() entered,  rowCount=" + rowCount);
  var editBody = document.getElementsByTagName('body')[0];
  var excepttable = GetElement(editBody,'table','excepttable');
  if(rowCount > 1) {
    for(var i=0;i < rowCount - 1;i++) {
      if(excepttable.rows[i].cells[0].getAttribute('inUse') == 'false') {
        for(var j = i + 1; j <= rowCount - 1;j++) { //look for cell to move
          if(excepttable.rows[j].cells[0].getAttribute('inUse') == 'true') {
            var myContainer = GetElement(excepttable.rows[j].cells[0],'div','outercontainer');
            excepttable.rows[i].cells[0].appendChild(excepttable.rows[j].cells[0].removeChild(myContainer));
            excepttable.rows[i].cells[0].setAttribute('inUse', 'true');
            excepttable.rows[i].cells[0].setAttribute('isSelected',excepttable.rows[j].cells[0].getAttribute('isSelected'));
            excepttable.rows[j].cells[0].setAttribute('inUse', 'false');
            excepttable.rows[j].cells[0].setAttribute('isSelected', 'false');
            break;
          }
        }
      }
    }
  }
}

function ExceptTablePruneRows() {
  ExceptTable_log("ExceptTablePruneRows() entered");
  var editBody = document.getElementsByTagName('body')[0];
  var excepttable = GetElement(editBody,'table','excepttable');
  for(var i = rowCount - 1;i >= 0;i--) {
    var busy = false;
    if(excepttable.rows[i].cells[0].getAttribute('inUse') == 'true') {
      busy = true;
      break;
    }
    if(!busy) {
      deleteExceptTableRow(i);
    }
    else {
      break;
    }
  }
}

function ExceptTableSortColumnByTime() {
  ExceptTable_log("ExceptTableSortColumnByTime() entered");
  var editBody = document.getElementsByTagName('body')[0];
  var excepttable = GetElement(editBody,'table','excepttable');
  if(rowCount > 1) {
    for(var i=0;i < rowCount - 1;i++) {
      var itime = GetElement(excepttable.rows[i].cells[0],'div','info').getAttribute('time');
      for(var j = i + 1; j < rowCount;j++) { //look for cell to move
        var jtime = GetElement(excepttable.rows[j].cells[0],'div','info').getAttribute('time');
        if(jtime < itime) {
          var iCellContent = excepttable.rows[i].cells[0].removeChild(GetElement(excepttable.rows[i].cells[0],'div','outercontainer'));
          var iSelected = excepttable.rows[i].cells[0].getAttribute('isSelected');
          excepttable.rows[i].cells[0].appendChild(excepttable.rows[j].cells[0].removeChild(GetElement(excepttable.rows[j].cells[0],'div','outercontainer')));
          excepttable.rows[i].cells[0].setAttribute('isSelected',excepttable.rows[j].cells[0].getAttribute('isSelected'));
          excepttable.rows[j].cells[0].appendChild(iCellContent);
          excepttable.rows[j].cells[0].setAttribute('isSelected', iSelected);
          if(excepttable.rows[i].cells[0].getAttribute('isSelected') == 'true') {
            currentCellSelection = excepttable.rows[i].cells[0];
            excepttable.rows[i].cells[0].setAttribute('bgColor','lightgrey');
          }
          else {
            excepttable.rows[i].cells[0].setAttribute('bgColor','white');
          }
          if(excepttable.rows[j].cells[0].getAttribute('isSelected') == 'true') {
            currentCellSelection = excepttable.rows[j].cells[0];
            excepttable.rows[j].cells[0].setAttribute('bgColor','lightgrey');
          }
          else {
            excepttable.rows[j].cells[0].setAttribute('bgColor','white');
          }
          itime = jtime;
          break;
        }
      }
    }
  }
}

function ExceptTableCopyDayCell() {
  ExceptTable_log("ExceptTableCopyDayCell() entered");
  if(!selectCellActive)
    return;
  var ielement = GetElement(currentCellSelection,'div','info');
  //addExceptTableDayCell(ielement.getAttribute('time'),ielement.getAttribute('setpoint'));
}

function ExceptTableClearDayCell() {
  ExceptTable_log("ExceptTableClearDayCell() entered");
  //deleteExceptTableDayCell();
}

function ExceptTableClearDayColumn() {
  ExceptTable_log("ExceptTableClearDayColumn() entered");
  //deleteExceptTableDayColumn();
}

/* dialog window support stuff */

var ExceptTableNav4 = ((navigator.appName == "Netscape") && (parseInt(navigator.appVersion) == 4));

var DialogWin = new Object();

function ExceptTableDeadEnd () {
  if(DialogWin.win && !DialogWin.win.closed) {
    if(DialogWin.onTop == true) {
      DialogWin.win.focus();
    }
    return false;
  }
}

var ExceptTableLinkClicks;

function ExceptTableDisableForms() {
  ExceptTable_log("ExceptTableDisableForms() entered");
  ExceptTableLinkClicks = new Array();
  for(var i = 0; i < document.forms.length; i++) {
    for(var j = 0; j < document.forms[i].elements.length; j++) {
      document.forms[i].elements[j].disabled = true;
    }
  }
  for(var i = 0; i < document.links.length; i++) {
    ExceptTableLinkClicks[i] = {click:document.links[i].onclick, up:null};
    ExceptTableLinkClicks[i].up = document.links[i].onmouseup;
    document.links[i].onclick = ExceptTableDeadEnd;
    document.links[i].onmouseup = ExceptTableDeadEnd;
    document.links[i].disabled = true;
  }
  window.onfocus = ExceptTableCheckModal;
  document.onclick = ExceptTableCheckModal;
}

function ExceptTableEnableForms() {
  ExceptTable_log("ExceptTableEnableForms() entered");
  for(var i = 0; i < document.forms.length; i++) {
    for(var j = 0; j < document.forms[i].elements.length; j++) {
      document.forms[i].elements[j].disabled = false;
    }
  }
  for(var i = 0; i < document.links.length; i++) {
    document.links[i].onclick = ExceptTableLinkClicks[i].click;
    document.links[i].onmouseup = ExceptTableLinkClicks[i].up;
    document.links[i].disabled = false;
  }
}

function BlockEvents() {
  ExceptTable_log("BlockEvents() entered");
  if(ExceptTableNav4) {
    window.captureEvents(Event.CLICK | Event.MOUSEDOWN | Event.MOUSEUP | Event.FOCUS);
    window.onclick = ExceptTableDeadEnd;
  }
  else {
    ExceptTableDisableForms();
  }
  window.onfocus = ExceptTableCheckModal;
}

function UnblockEvents() {
  ExceptTable_log("UnblockEvents() entered");
  if(ExceptTableNav4) {
    window.releaseEvents(Event.CLICK | Event.MOUSEDOWN | Event.MOUSEUP | Event.FOCUS);
    window.onclick = null;
    window.onfocus = null;
  }
  else {
    ExceptTableEnableForms();
  }
}

function ExceptTableDoAddDay() {
  ExceptTable_log("ExceptTableDoAddDay() entered");
  addExceptTableDayCell(DialogWin.newTime,DialogWin.newSetpoint);
  ExceptTableSortColumnByTime();
  //re-enable modal focus behavior of parent.opener.DialogWin
  if(parent.opener && parent.opener.DialogWin) {
    parent.opener.DialogWin.onTop = true;
  }
}

function ExceptTableDoChangeDay() {
  ExceptTable_log("ExceptTableDoChangeDay() entered");
  try {
    var ielement = GetElement(DialogWin.elem,'div','info');
    var ndelement = GetElement(DialogWin.elem,'div','nodedisplay');
    var oldTime = ielement.getAttribute('time');
    ielement.setAttribute('time', DialogWin.newTime);
    ielement.setAttribute('setpoint', DialogWin.newSetpoint);
    ielement.setAttribute('dialog_active',true);
    ndelement.innerHTML = DialogWin.newTime + " " + DialogWin.newSetpoint;
    if(oldTime != DialogWin.newTime) {
      ExceptTableSortColumnByTime();
    }
  }
  catch(err) {
    alert('ERROR: ' + err.message + '\nPlease check node path for this widget.');
  }
  //re-enable modal focus behavior of parent.opener.DialogWin
  if(parent.opener && parent.opener.DialogWin) {
    parent.opener.DialogWin.onTop = true;
  }
}

function ExceptTableOpenAddDayDialog() {
  ExceptTable_log("ExceptTableOpenAddDayDialog() entered");
  ExceptTableOpenDialog('day','add',null);
}

function ExceptTableOpenChangeDayDialog(evt) {
  ExceptTable_log("ExceptTableOpenChangeDayDialog() entered");
  evt = (evt) ? evt : ((event) ? event : null);
  if(evt.detail) {
    ExceptTable_log("ExceptTableOpenChangeDayDialog(), evt.detail=" + evt.detail);
  }
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myContainer = elem.parentNode.parentNode; //outercontainer div of ExceptTable widget
  ExceptTable_log("ExceptTableOpenChangeDayDialog(), myContainer element = " + myContainer.getAttribute('element'));
  //disable modal focus behavior of parent.opener.DialogWin
  if(parent.opener && parent.opener.DialogWin) {
    parent.opener.DialogWin.onTop = false;
  }
  ExceptTableOpenDialog('day','change',myContainer);
}

function ExceptTableOpenDialog(type,cmd,container) {
  /*var ielement = GetElement(container,'div','info');
  if(ielement.getAttribute('dialog_enabled') == 'false') {
    ExceptTable_log("ExceptTableOpenDialog(), early return, dialog_enabled=false");
    return; //return if dialog disabled
  }*/
  if(!DialogWin.win || (DialogWin.win && DialogWin.win.closed)) {
    ExceptTable_log("ExceptTableOpenDialog(), window doesn't exist or is closed");
    DialogWin.cmd = cmd;
    DialogWin.onTop = true;
    DialogWin.elem = container;
    if(type == 'day') {
      DialogWin.url = '/webapi/editday.htm';
      DialogWin.width = 240;
      DialogWin.height = 200;
    }
    else {
      DialogWin.url = '/webapi/editexcept.htm';
      DialogWin.width = 650;
      DialogWin.height = 360;
    }
    DialogWin.addDayFunc = ExceptTableDoAddDay;
    DialogWin.changeDayFunc = ExceptTableDoChangeDay;
    DialogWin.addExceptFunc = null;
    DialogWin.changeExceptFunc = null;
    DialogWin.args = '';
    DialogWin.newDate = '';
    DialogWin.newTime = '';
    DialogWin.newSetpoint = '';
    DialogWin.newExceptName = '';
    DialogWin.newStartDate = '';
    DialogWin.newEndDate = '';
    DialogWin.name = (new Date()).getSeconds().toString();
    ExceptTable_log("ExceptTableOpenDialog(), before attr calc");
    if(parent.screenX) { //Navigator 4+
      ExceptTable_log("ExceptTableOpenDialog(), parent.screenX defined, Navigator branch taken");
      DialogWin.left = parent.screenX +
        ((parent.outerWidth - DialogWin.width) / 2);
      DialogWin.top = parent.screenY +
        ((parent.outerHeight - DialogWin.height) / 2);
      var attr = "screenX=" + DialogWin.left +
        ",screenY=" + DialogWin.top + ",resizable=no,width=" +
        DialogWin.width + ",height=" + DialogWin.height;
    }
    else if(parent.screenLeft) { //Windows IE5+
      ExceptTable_log("ExceptTableOpenDialog(), parent.screenLeft defined, Windows IE branch taken");
      var CSSCompat = (parent.document.compatMode && parent.document.compatMode != "BackCompat");
      ExceptTable_log("ExceptTableOpenDialog(), CSSCompat=" + CSSCompat);
      parent.outerWidth = (CSSCompat) ? parent.document.body.parentElement.clientWidth :
        parent.document.body.clientWidth;
      parent.outerHeight = (CSSCompat) ? parent.document.body.parentElement.clientHeight :
        parent.document.body.clientHeight;
      parent.outerHeight -= 80;
      DialogWin.left = parseInt(parent.screenLeft +
        ((parent.outerWidth - DialogWin.width) / 2));
      DialogWin.top = parseInt(parent.screenTop +
        ((parent.outerHeight - DialogWin.height) / 2));
      var attr = "left=" + DialogWin.left +
        ",top=" + DialogWin.top + ",resizable=no,width=" +
        DialogWin.width + ",height=" + DialogWin.height;
    }
    else {
      ExceptTable_log("ExceptTableOpenDialog(), generic branch taken");
      DialogWin.left = (screen.width - DialogWin.width) / 2;
      DialogWin.top = (screen.height - DialogWin.height) / 2;
      var attr = "left=" + DialogWin.left + ",top=" +
        DialogWin.top + ",resizable=no,width=" + DialogWin.width +
        ",height=" + DialogWin.height;
    }
    ExceptTable_log("ExceptTableOpenDialog(), after attr calc");
    if(!DialogWin.win){
      ExceptTable_log("ExceptTableOpenDialog(), win not defined");
    }
    else {
      ExceptTable_log("ExceptTableOpenDialog(), win defined");
    }
    ExceptTable_log("ExceptTableOpenDialog(), before window.open(), url=" + DialogWin.url +
      ", name=" + DialogWin.name + ", attr=" + attr);
    DialogWin.win = window.open(DialogWin.url, DialogWin.name, attr);
    ExceptTable_log("ExceptTableOpenDialog(), after window.open(), DialogWin.win.name=" + DialogWin.win.name);
    setTimeout("DialogWin.win.focus()", 250);
  }
  else {
    if(DialogWin.onTop == true) {
      setTimeout("DialogWin.win.focus()", 250);
    }
  }
}

function ExceptTableDeleteDayCell() {
  ExceptTable_log("ExceptTableDeleteDayCell() entered");
  deleteExceptTableDayCell();
}

function ExceptTableDuplicateDayCell() {
  ExceptTable_log("ExceptTableDuplicateDayCell() entered");
  if(!selectCellActive)
    return;
  var ielement = GetElement(currentCellSelection,'div','info');
  addExceptTableDayCell(ielement.getAttribute('time'),ielement.getAttribute('setpoint'));
  ExceptTableSortColumnByTime();
}

function ExceptTableClearColumn() {
  ExceptTable_log("ExceptTableClearColumn() entered");
  deleteExceptTableDayColumn();
}




function ExceptTableCheckModal() {
  ExceptTable_log("ExceptTableCheckModal() entered");
  setTimeout("ExceptTableFinishCheckModal()", 250);
  return true;
}

function ExceptTableFinishCheckModal() {
  ExceptTable_log("ExceptTableFinishCheckModal() entered");
  if(DialogWin.win && !DialogWin.win.closed) {
    if(DialogWin.onTop == true) {
      ExceptTable_log("ExceptTableFinishCheckModal(), before focus");
      DialogWin.win.focus();
      ExceptTable_log("ExceptTableFinishCheckModal(), after focus");
    }
  }
}

function ExceptTable_msg(msg) {
  ExceptTable_log("ExceptTable_msg, msg=" + msg);
  parent.Scheduler_msg(msg);
}

var mySchedArray = null;
var mySchedHolderArray = null;
var myNewSchedHolderArray = null;

function ExceptTable_load() {
  ExceptTable_log("ExceptTable_load() entered");
  ExceptTableInit();
  window.setTimeout("ExceptTable_loadPhase2()",0);
}

function ExceptTable_loadPhase2() {
  ExceptTable_log("ExceptTable_loadPhase2() entered");
  if(parent.myCmd == 'change') {
    ExceptTable_populateExceptionColumn();
  }
}

function ExceptTable_populateExceptionColumn() {
  var myEntries = parent.opener.myExceptions[parent.myExceptionName].entries;
  if(myEntries == null)
     return;
  for(var i = 0; i < myEntries.length; i++) {
    addExceptTableDayCell(myEntries[i][0],myEntries[i][1]);
  }
  ExceptTableSortColumnByTime();
}

function ExceptTable_cleanScheduleHolder(compareStr) {
  ExceptTable_log("ExceptTable_cleanScheduleHolder() entered");
  var myTempArray = new Array();
  for(var i = 0; i < mySchedHolderArray.length; i++) {
    ExceptTable_log("ExceptTable_cleanScheduleHolder(), mySchedHolderArray[" + i + "][SCHEDULESNAME]=" + mySchedHolderArray[i][SCHEDULESNAME]);
    if(!(mySchedHolderArray[i][SCHEDULESNAME] == compareStr)) {
      myTempArray.push(mySchedHolderArray[i]);
    }
  }
  return myTempArray;
}

function buildExceptScheduleForSave() {
  ExceptTable_log("ExceptTable_buildExceptScheduleForSave(), rowCount=" + rowCount);
  var editBody = document.getElementsByTagName('body')[0];
  var excepttable = GetElement(editBody,'table','excepttable');
  if(rowCount > 0) {
    var mySchedule = new Array();
    for(var j = 0; j < rowCount; j++) {
      var myScheduleEntry = new Array(2);
      var ielement = GetElement(excepttable.rows[j].cells[0],'div','info');
      myScheduleEntry[0] = ielement.getAttribute('time');
      myScheduleEntry[1] = ielement.getAttribute('setpoint');
      mySchedule.push(myScheduleEntry);
    }
    ExceptTable_log("ExceptTable_buildExceptScheduleForSave(), mySchedule=" + array2String(mySchedule));
    return mySchedule;
  }
  else {
    return null;
  }
}
