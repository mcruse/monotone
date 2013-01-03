"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
# rzutils -- Python module to support application launch
# $Name: mediator_3_1_2_branch $
# $Id: rzutils.py 20568 2011-06-14 01:50:43Z dleimbro $

import os
import fnmatch
import sys
from mpx import properties
from mpx.lib import msglog
import time
import calendar
import ConfigParser
from node import as_node
import pickle
import rzcache

#globals for this module
schedbckupdir = 'schedbckup'
timeroot = '/services/time'
omegaconfigdir = os.path.join(properties.HTTP_ROOT, 'omega')


omegaconfigtype = '.conf'
EXCLUDES = ['admin.html', 'index.html', 'login.html','home_top.html','home_nav.html','home_main.html','home_bottom.html', 'redirect.html', 'msglog', 'webapi', 'omega']
DEPRECATED = ('PHSchedule.wjs',)

def testmessage():
    message = 'Test Message from inside rzutils module\n'
    return message

def genScheduleHolderListScript():
    theList = []
    scheduleholderlist = []
    scheduleholderroot = ['/services/time/local', '/services/time/UTC']
    scheduleprefix = 'RZSched_'
    for myholderroot in scheduleholderroot:
        myholderrootnode = as_node(myholderroot)
        rootchildlist = myholderrootnode.children_names()
        rootchildlist.sort()
        for myholder in rootchildlist:
            myholderpath = myholderroot + '/' + myholder
            myholdernode = as_node(myholderpath)
            try:
                if myholdernode.hasattr('__node_id__'):
                    holderchildlist = myholdernode.children_names()
                    for name in holderchildlist:
                        if name.find(scheduleprefix) == 0:
                            scheduleholderlist.append(myholderpath)
                            break
            except:
                pass
    if scheduleholderlist:
        theList.append('<select id="theSchedule">')
        for f in scheduleholderlist:
            theList.append('<option value="%s">%s</option>' % (f,f))
        theList.append('</select><br><br>')
    return theList

def genScheduleBackupListScript(root, scheduleholder, scheduleprefix):
    theList = []
    scheduleslist = []
    prefixlen = len(scheduleprefix)
    timelen = len(timeroot) + 1
    shortpath = scheduleholder[timelen:]
    shortpathitems = shortpath.split('/')
    scheddir = os.path.join(root, schedbckupdir, shortpathitems[0])
    schedholderlist = os.listdir(scheddir)
    for holder in schedholderlist:
        fn = os.path.join(root, scheddir, holder)
	if os.path.exists(fn):
            tmpFile = open(fn, 'r')
	    backupvalue = pickle.load(tmpFile)
	    tmpFile.close()
	    for backupschedule in backupvalue:
                scheduleslist.append(holder + '/' + backupschedule[0][prefixlen:])
    if scheduleslist:
        scheduleslist.sort()
        theList.append('<select id="theBackupList">')
        for f in scheduleslist:
            theList.append('<option value="%s">%s</option>' % (f,f))
        theList.append('</select><br><br>')
    return theList

def genScheduleListScript(scheduleholder, scheduleprefix):
    theList = []
    schedulelist = []
    mynode = as_node(scheduleholder)
    childlist = mynode.children_names()
    childlist.sort()
    plen = len(scheduleprefix)
    schedulelist = [name[plen:] for name in childlist if name.find(scheduleprefix) == 0]
    if schedulelist:
        theList.append('<select id="theSchedule">')
        for f in schedulelist:
            theList.append('<option value="%s">%s</option>' % (f,f))
        theList.append('</select><br><br>')
    return theList

def caseIndependentSort(something, other):
    something, other = something.lower(), other.lower()
    return(cmp(something, other))

def genWidgetScript(listroot):
    return rzcache.COMMON_CACHE.lazy_get(_genWidgetScript, (listroot,))

def _genWidgetScript(listroot):
    theList = []

    # Collect input and output arguments into one bunch
    class Bunch:
        def __init__(self, **kwds): self.__dict__.update(kwds)
    arg = Bunch(listroot=listroot, widget_files=[])

    def getWidgetList(arg,dirname,names):
        for name in names:
            x = os.path.join(dirname,name)
            if os.path.isfile(x):            
                if x[-4:] == '.wjs' and not name in DEPRECATED:
                    arg.widget_files.append(x[len(arg.listroot):])       

    os.path.walk(os.path.join(listroot, 'webapi/js'), getWidgetList, arg)
    arg.widget_files.sort(caseIndependentSort)
    for f in arg.widget_files:
        theList.append(
            '<script src="%s" widget="true" type="text/javascript" ></script>'
            % (f)
            )

    return theList

def excludeWEFile(filename):
    for exclude in EXCLUDES:
        if fnmatch.fnmatch(filename, exclude):
            return True
    return False

def matchWEFile(pattern_list, return_folders, fullname, basename):
    if return_folders or os.path.isfile(fullname):
        for pattern in pattern_list:
            lowname = basename.lower()
            if fnmatch.fnmatch(lowname, pattern):
                return True
    return False

def listWEFiles(listroot, patterns='*', show_all_files='false', recurse=1, return_folders=0):

    # Expand patterns from semicolon-separated string to list
    pattern_list = patterns.split(';')
    # Collect input and output arguments into one bunch
    class Bunch:
        def __init__(self, **kwds): self.__dict__.update(kwds)
    arg = Bunch(recurse=recurse, pattern_list=pattern_list, show_all_files=show_all_files,
        return_folders=return_folders, results=[])

    def visit(arg, dirname, files):
        # Append to arg.results all relevant files (and perhaps folders)
        files.sort(caseIndependentSort)
        if arg.show_all_files == 'false' and listroot == dirname:
            for i in range(len(files) - 1, -1, -1):
                if excludeWEFile(files[i]):
                    del files[i]
                    continue

        for name in files:
            fullname = os.path.normpath(os.path.join(dirname, name))
            if matchWEFile(arg.pattern_list, arg.return_folders,
                           fullname, name):
                arg.results.append(fullname[len(listroot)+1:])

        # Block recursion if recursion was disallowed
        if not arg.recurse: files[:]=[]

    os.path.walk(listroot, visit, arg)

    return arg.results

def load_config(filename):
    try:
        cp = ConfigParser.ConfigParser()
        fp = open(filename, 'r')
        cp.readfp(fp)
        fp.close()
    except Exception,e:
        return None
    return cp

def get_option(config, section, option):
    if config.has_section(section) and config.has_option(section, option):
        return config.get(section, option)
    return ''

def getFeatureKeyFileName():
    serialnum = properties.SERIAL_NUMBER
    filename = serialnum.rstrip() + omegaconfigtype
    return filename

def isAllowed(section, option):
    # rzutils licensing no longer used - log a message and return 1
    msg = 'Deprecated licensing call (%s:%s) made' % (section, option)
    msglog.log('broadway', msglog.types.INFO, msg)
    return 1

def _isAllowed(section, option):
    serialnum = properties.SERIAL_NUMBER
    serialval = serialnum.strip()
    filename = serialnum.rstrip() + omegaconfigtype
    fullname = os.path.join(omegaconfigdir, filename)
    if os.path.exists(fullname):
        config = load_config(fullname)
        compareval = get_option(config, section, option)
        if compareval == '':
            return 0
        dateval = get_option(config, 'identity', 'creation')
        if dateval == '':
            return 0
        datetuple = time.strptime(dateval)
        dateseconds = calendar.timegm(datetuple)
        datestring = '%s' % (dateseconds)
        customer = get_option(config, 'identity', 'customer')
        if customer == '':
            return 0
        customerval = customer.strip()
        model = get_option(config, 'identity', 'model')
        if model == '':
            return 0
        modelval = model.strip()
        tokenval = serialval + datestring[4:] + customerval + datestring[:4] + os.time.split()[0] + option.strip() + modelval
        command = 'echo %s | md5sum' % (tokenval)
        child = os.popen(command)
        resultval = child.read()
        err = child.close()
        if err:
            raise RuntimeError, 'rzutils: checksum failed with exit code %d' % (err)
        if len(resultval) < 32:
            return 0
        #return resultval[:32] + ',' + compareval[:32]
        if resultval[:32] == compareval[:32]:
            return 1 #option is allowed
    return 0


def isApplicationAllowed(applname):
    return isAllowed('applications', applname)

def isInterfaceAllowed(ifname):
    return isAllowed('interfaces', ifname)

def listOmegaConfig():
    theList = []
    serialnum = properties.SERIAL_NUMBER
    filename = serialnum.rstrip() + omegaconfigtype
    fullname = os.path.join(omegaconfigdir, filename)
    if os.path.exists(fullname):
        config = load_config(fullname)
        sectionlist = config.sections()
        for section in sectionlist:
            theList.append('[' + section + ']')
            optionlist = config.options(section)
            for option in optionlist:
                optionval = get_option(config, section, option)
                theList.append(option + ' = ' + optionval)
            theList.append('')
        dateval = get_option(config, 'identity', 'creation')
        datetuple = time.strptime(dateval)
        dateseconds = calendar.timegm(datetuple)
        datestring = '%s' % (dateseconds)
        theList.append(datestring)
    return theList


#
# WEFS = WebWexpress File Selector
#
# This section has been extend to manage a the "select/options" lists created
# by the assorted gen* file scanning functions in the generic rzcache.
#

def _wefs_cmp_entries(a, b):
    open_select_frag  = '<select' # Always first
    close_select_frag = '</selec' # Always last
    assert len(open_select_frag) == len(close_select_frag)
    first_frag_len = len(open_select_frag)
    a_frag = a[:first_frag_len]
    if a_frag == open_select_frag:
        return -1
    if a_frag == close_select_frag:
        return 1
    b_frag = b[:first_frag_len]
    if b_frag == open_select_frag:
        return 1
    if b_frag == close_select_frag:
        return -1
    return caseIndependentSort(a,b)

def _as_wefs_file_option(listroot, relativename):
    option = '<option value="%s">%s</option>' % (relativename, relativename)
    return option

def _as_wefs_page_option(listroot, relativename):
    option = '<option value="%s">%s</option>' % (
        relativename, relativename.replace('.wdx','')
        )
    return option

_WEFS_CACHE_HANDLERS = {
    '_genFileSelectorScript': {
        'create_option':_as_wefs_file_option,
        'compare':_wefs_cmp_entries,
        },
    '_genCopyMultipleSelectorScript': {
        'create_option':_as_wefs_file_option,
        'compare':_wefs_cmp_entries,
        },
    '_genWebsitebuilderSelectorScript': {
        'create_option':_as_wefs_file_option,
        'compare':_wefs_cmp_entries,
        },
    '_genFileSelectorScriptMultiple': {
        'create_option':_as_wefs_file_option,
        'compare':_wefs_cmp_entries,
        },
    '_genSitePageSelectorScript': {
        'create_option':_as_wefs_page_option,
        'compare':_wefs_cmp_entries,
        'convert_basename':lambda x: x.replace('.html','.wdx'),
        },
    }

def wefs_cache(filename):
    for cache_key in rzcache.COMMON_CACHE.cache_keys():
        func_key = cache_key.key[0]
        cache_handler = _WEFS_CACHE_HANDLERS.get(repr(func_key))
        if cache_handler is None:
            continue
        create_option = cache_handler['create_option']
        compare = cache_handler['compare']
        convert_basename = cache_handler.get('convert_basename', lambda x: x)
        args_key = cache_key.key[1]
        args_tuple = args_key.arg.arg
        listroot = args_tuple[0].arg
        pattern_list=args_tuple[1].arg.split(";")
        show_all_files=args_tuple[2].arg
        if len(args_tuple) > 3:
            recurse=args_tuple[3].arg
        else:
            recurse=1
        if len(args_tuple) > 4:
            return_folders=args_tuple[4].arg
        else:
            return_folders=0
        basename = convert_basename(os.path.basename(filename))
        
        if (show_all_files == 'false'
            and excludeWEFile(basename)):
            continue
        if not recurse and os.path.dirname(filename) != listroot:
            continue
        if matchWEFile(pattern_list, return_folders, filename, basename):
            if filename.startswith(listroot):
                relativename = filename[len(listroot) + 1:] # Hack for final /
                option = create_option(listroot, relativename)
                rzcache.COMMON_CACHE.new_sorted_entry(cache_key, option,
                                                      compare)
            elif os.path.isfile(os.path.join(listroot, basename)):
                # Hack for PageSelect
                option = create_option(listroot, basename)
                rzcache.COMMON_CACHE.new_sorted_entry(cache_key, option,
                                                      compare)
    return

def wefs_uncache(filename):
    for cache_key in rzcache.COMMON_CACHE.cache_keys():
        func_key = cache_key.key[0]
        cache_handler = _WEFS_CACHE_HANDLERS.get(repr(func_key))
        if cache_handler is None:
            continue
        create_option = cache_handler['create_option']
        convert_basename = cache_handler.get('convert_basename', lambda x: x)
        args_key = cache_key.key[1]
        args_tuple = args_key.arg.arg
        listroot = args_tuple[0].arg
        basename = convert_basename(os.path.basename(filename))
        if filename.startswith(listroot):
            relativename = filename[len(listroot) + 1:] # Hack for final /
            option = create_option(listroot, relativename)
            rzcache.COMMON_CACHE.del_entry(cache_key, option)
        elif not os.path.isfile(os.path.join(listroot, basename)):
            # Hack for PageSelect
            option = create_option(listroot, basename)
            rzcache.COMMON_CACHE.del_entry(cache_key, option)
    return

def _genFileSelectorScript(root, patterns, allfiles):
    theList = []
    FILES = listWEFiles(root, patterns, allfiles)
    theList.append('<select id="theFile" name="theFile">')
    for f in FILES:
        theList.append(_as_wefs_file_option(root, f))
    theList.append('</select><br><br>')
    return theList

def genFileSelectorScript(root, patterns, allfiles):
    return rzcache.COMMON_CACHE.lazy_get(_genFileSelectorScript,
                                         (root, patterns, allfiles,))

def _genSitePageSelectorScript(root, patterns, allfiles):
    theList = []
    FILES = listWEFiles(root, patterns, allfiles, 0)
    theList.append('<select id="theFile" name="theFile">')
    for f in FILES:
        theList.append(_as_wefs_page_option(root, f))
    theList.append('</select><br><br>')
    return theList

def genSitePageSelectorScript(root, patterns, allfiles):
    return rzcache.COMMON_CACHE.lazy_get(_genSitePageSelectorScript,
                                         (root, patterns, allfiles,))

def _genWebsitebuilderSelectorScript(root, patterns, allfiles, changehandler):
    theList = []
    FILES = listWEFiles(root, patterns, allfiles)
    theList.append('<select name="available" onchange="%s">' %
                   changehandler)
    for f in FILES:
        theList.append(_as_wefs_file_option(root, f))
    theList.append('</select>')
    return theList

def genWebsitebuilderSelectorScript(root, patterns, allfiles, changehandler):
    return rzcache.COMMON_CACHE.lazy_get(_genWebsitebuilderSelectorScript,
                                         (root, patterns, allfiles,
                                          changehandler,))

def _genCopyMultipleSelectorScript(root, patterns, allfiles, changehandler):
    theList = []
    FILES = listWEFiles(root, patterns, allfiles)
    theList.append('<select id="theFile" name="theFile" onchange="%s">' %
                   (changehandler))
    for f in FILES:
        theList.append(_as_wefs_file_option(root, f))
    theList.append('</select><br><br>')
    return theList

def genCopyMultipleSelectorScript(root, patterns, allfiles, changehandler):
    return rzcache.COMMON_CACHE.lazy_get(_genCopyMultipleSelectorScript,
                                         (root, patterns, allfiles,
                                          changehandler,))

def _genFileSelectorScriptMultiple(root, patterns, allfiles):
    theList = []
    FILES = listWEFiles(root, patterns, allfiles)
    theList.append(
        '<select id="theFile" name="theFile" size="10" multiple>'
        )
    for f in FILES:
        theList.append(_as_wefs_file_option(root, f))
    theList.append('</select><br><br>')
    return theList

def genFileSelectorScriptMultiple(root, patterns, allfiles):
    return rzcache.COMMON_CACHE.lazy_get(_genFileSelectorScriptMultiple,
                                         (root, patterns, allfiles,))
