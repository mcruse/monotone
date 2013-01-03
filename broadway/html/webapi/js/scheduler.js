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
/*
Purpose: Scheduler editor
$Name: mediator_3_1_2_branch $
$Id: scheduler.js 20101 2011-03-06 16:02:15Z bhagn $
*/
var HTML;
var SchedulerDebug = false;
var SchedulerEditor = true;
var SchedulerProtocol = window.location.protocol;
var SchedulerHostname = window.location.hostname;
var Scheduler_RETRIES = 0;
var Scheduler_MAX_RETRIES = 100;
var WIDGET_BORDER = '1px solid blue';
var CURRENT_ID = null;
var HTTP_ERRORS = new Object();
HTTP_ERRORS[400] = 'Bad Request';
HTTP_ERRORS[401] = 'Unauthorized';
HTTP_ERRORS[402] = 'Payment Required';
HTTP_ERRORS[403] = 'Forbidden';
HTTP_ERRORS[404] = 'Not Found';
HTTP_ERRORS[405] = 'Method Not Allowed';
HTTP_ERRORS[406] = 'Not Acceptable';
HTTP_ERRORS[407] = 'Proxy Authentication Required';
HTTP_ERRORS[408] = 'Request Timeout';
HTTP_ERRORS[409] = 'Conflict';
HTTP_ERRORS[410] = 'Gone';
HTTP_ERRORS[411] = 'Length Required';
HTTP_ERRORS[412] = 'Precondition Failed';
HTTP_ERRORS[413] = 'Request Entity Too Large';
HTTP_ERRORS[414] = 'Request-URI Too Long';
HTTP_ERRORS[415] = 'Unsupported Media Type';
HTTP_ERRORS[416] = 'Requested Range Not Satisfiable';
HTTP_ERRORS[411] = 'Expectation Failed';

var Scheduler_request;
var SchedulerMsgTypes = new Object();
SchedulerMsgTypes.NORMAL = 'black';
SchedulerMsgTypes.ERROR = 'red';
var SchedulerMsgTimeout;
var startRetryCount = 600;
var IFRAMENAME = '';
var IFRAME = null;

function Scheduler_log(msg) {
  if(SchedulerDebug) {
    msglog(msg);
  }
}

function Scheduler_msg(msg,type){
  if (arguments.length == 1){
    type = SchedulerMsgTypes.NORMAL;
   }
   document.getElementById('msg').innerHTML = msg;
   document.getElementById('msg').style.color = type;
}

function Scheduler_updateScheduleNameDisplay(name) {
  document.getElementById('schedulename').innerHTML = name;
}

function Scheduler_start(){
  Scheduler_log("Scheduler_start(), at top");
  Scheduler_msg('Initializing...');

  if(EDITMODE == 'SAVEONLY') {
    document.getElementById('saveascontent').style.visibility = 'hidden';
    document.getElementById('deletecontent').style.visibility = 'hidden';
  }

  //create iframe for editing 
  var iFrameHolder = document.getElementById("schedFrameHolder");
  var childFrame = document.createElement("iframe");
  IFRAMENAME = "editFrame";
  childFrame.setAttribute("id",IFRAMENAME);
  childFrame.setAttribute("name",IFRAMENAME);
  childFrame.setAttribute("title","content");
  childFrame.src = '/webapi/emptypage.html';
  childFrame.width = '710';
  childFrame.height = '560';
  childFrame.scrolling = 'auto';
  iFrameHolder.appendChild(childFrame);
  window.setTimeout("Scheduler_startPhase2();",0); //fixes IE appendChild() race
}

function Scheduler_startPhase2() {
  Scheduler_log("Scheduler_startPhase2(), at top");
  //load iframe with target file
  var browserIE = new RegExp('internet explorer','gi');
  if(browserIE.test(navigator.appName)) {
    //Internet Explorer
    document.getElementById(IFRAMENAME).src = document.getElementById("schedFrameHolder").getAttribute("editFile");
    waitForIFrameToLoad();
  }
  else {
    //Netscape Navigator
    document.getElementById(IFRAMENAME).onload = Scheduler_startPhase3;
    document.getElementById(IFRAMENAME).src = document.getElementById("schedFrameHolder").getAttribute("editFile");
  }
}

function waitForIFrameToLoad() {
  //Scheduler_log("waitForIFrameToLoad(), at top");
  var iFrameDoc = document.getElementById(IFRAMENAME).contentWindow.document;
  if(iFrameDoc.readyState == "complete") {
    Scheduler_startPhase3();
  }
  else {
    window.setTimeout("waitForIFrameToLoad()",1);
  }
}

function Scheduler_startPhase3() {
  Scheduler_log("Scheduler_startPhase3(), at top");
  //Scheduler_msg(''); //clear message area
  //save global reference to iframe
  IFRAME = document.getElementById(IFRAMENAME);
}

function addDayCell(col) {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.currentCol = col;
  editWin.SchedTableOpenAddDayDialog();
}

function copyDayCell(col) {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.currentCol = col;
  editWin.SchedTableCopyDayCell();
}

function cutDayCell(col) {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.currentCol = col;
  editWin.SchedTableCutDayCell();
}

function deleteDayCell(col) {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.currentCol = col;
  editWin.SchedTableDeleteDayCell();
}

function pasteDayCell(col) {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.currentCol = col;
  editWin.SchedTablePasteDayCell();
}

function clearDayColumn(col) {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.currentCol = col;
  editWin.SchedTableClearDayColumn();
}

function copyDayToColumn(fromCol,toCol) {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.currentCol = fromCol;
  editWin.SchedTableCopyDayColumn(fromCol,toCol);
}

function addExceptCell() {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.currentCol = editWin.EXCEPTCOL;
  editWin.SchedTableOpenAddExceptDialog();
}

function deleteExceptCell() {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.currentCol = editWin.EXCEPTCOL;
  editWin.SchedTableDeleteExceptCell();
}

function duplicateExceptCell() {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.currentCol = editWin.EXCEPTCOL;
  editWin.SchedTableDuplicateExceptCell();
}

function renameExceptCell() {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.currentCol = editWin.EXCEPTCOL;
  editWin.SchedTableRenameExceptCell();
}

function clearExceptColumn() {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.currentCol = editWin.EXCEPTCOL;
  editWin.SchedTableClearExceptColumn();
}

var saveScheduleWinRef = null;
function Scheduler_saveScheduleWin(){
  // IE, in IE you can't set onclick events to a string
  // you have to set it to a reference of a function 
  var w = '600';
  var h = '600';
  var features = "menubar=false;toolbar=false,height=1,width=1;resizeable,scrollbars";
         
  //saveScheduleWinRef = window.open("/webapi/scheduleSelector.htm?savefunction=Scheduler_scheduleSelectorCloser&schedulename=" + SCHEDULENAME,
    //"scheduleSelector",features);
  saveScheduleWinRef = window.open("/webapi/psp/scheduleselector.psp?savefunction=Scheduler_scheduleSelectorCloser&scheduleholder=" +
    SCHEDULEHOLDER + "&scheduleprefix=" + SCHEDULEPREFIX + "&schedulename=" + SCHEDULENAME,"scheduleSelector",features);
  
  var height = window.screen.availHeight;
  var width = window.screen.availWidth;
  var left_point = parseInt(width/2) - parseInt(w/2);
  var top_point =  parseInt(height/2) - parseInt(h/2);
  saveScheduleWinRef.moveTo(left_point,top_point);

  saveScheduleWinRef.resizeTo(w,h);
  saveScheduleWinRef.focus();
}

function Scheduler_scheduleSelectorCloser() {
  var newschedulename =  saveScheduleWinRef.document.getElementById('sched_name').value;
  if (saveScheduleWinRef.opener){
    if (newschedulename == ''){
      alert('You must enter a schedule name to save the schedule.');
    }
    else{
      //valid file name format
      if(Scheduler_saveAs(newschedulename)) {
        saveScheduleWinRef.close();
        saveScheduleWinRef = null;
      }
    }
  }
  else{
    alert('schedule name:' + SCHEDULENAME);
  }
}

function Scheduler_save(){
  var msg;
  msg = "Do you really want to save?";
  if(confirm(msg)){
    Scheduler_msg('Saving "' + SCHEDULENAME + '" schedule...');
    var editWin = document.getElementById(IFRAMENAME).contentWindow;
    editWin.SchedTable_saveSchedToMediator();
    return true;
  }
  else{
    Scheduler_msg('Save Canceled');
    return false;
  }
}

function Scheduler_saveAs(schedname){
  var msg;
  msg = "Do you really want to save?";
  if(confirm(msg)){
    Scheduler_msg('Saving schedule as "' + schedname + '"...');
    var editWin = document.getElementById(IFRAMENAME).contentWindow;
    editWin.SchedTable_addSchedToMediator(schedname);
    return true;
  }
  else{
    Scheduler_msg('Save Canceled');
    return false;
  }
}

function Scheduler_delete(){
  var msg;
  msg = "Use the RZ configTOOL to remove RZSched nodes from the /services/time/local/time_schedules_1 node.";
  alert(msg);
  /*msg = "Warning: deleting a schedule may cause a value change in dependent nodes! Do you want to continue?";
  if(confirm(msg)){
    msg = "Do you really want to delete?";
    if(confirm(msg)){
      Scheduler_msg('Deleting "' + SCHEDULENAME + '" schedule...');
      var editWin = document.getElementById(IFRAMENAME).contentWindow;
      editWin.SchedTable_deleteSchedFromMediator();
      return true;
    }
  }
  Scheduler_msg('Delete Canceled');*/
  return false;
}

function Scheduler_reload(){
  Scheduler_log("Scheduler_reload, at top");
  Scheduler_start();
}

function Scheduler_close(){
  Scheduler_log("Scheduler_close, at top");
  //window.close();
  top.location = "/scheduleconfig";
}
