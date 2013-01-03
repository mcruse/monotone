"""
Copyright (C) 2009 2011 Cisco Systems

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
def run(psp,request,response):
    # $Name: mediator_3_1_2_branch $
    # $Id: mediatorname.py 20101 2011-03-06 16:02:15Z bhagn $
    #returns table display of Mediator hostname, IP address, and location
    from mpx import properties
    import os
    import sys
    import socket
    import ConfigParser
    
    CONFIGURATION_FILE = os.path.join(properties.ETC_DIR,'mpxinit.conf')
    
    if request.get_protocol() == 'http':
        root = properties.HTTP_ROOT
    else:
        root = properties.HTTPS_ROOT
    
    #set query string defaults
    hostname = 'true'
    ipaddress = 'true'
    location = 'true'
    bgcolor = '#ffffff'
    fontfamily = 'Verdana, Arial, Helvetica, sans-serif'
    fontcolor = '#000000'
    #override with query string values
    qs = request.get_query_dictionary()
    if qs.has_key('hostname'):
        hostname = '%s' % qs['hostname']
    if qs.has_key('ipaddress'):
        ipaddress = '%s' % qs['ipaddress']
    if qs.has_key('location'):
        location = '%s' % qs['location']
    if qs.has_key('bgcolor'):
        bgcolor = '%s' % qs['bgcolor']
    if qs.has_key('fontfamily'):
        fontfamily = '%s' % qs['fontfamily']
    if qs.has_key('fontcolor'):
        fontcolor = '%s' % qs['fontcolor']
    
    def load_config(filename):
        cp = ConfigParser.ConfigParser()
        fp = open(filename, 'r')
        cp.readfp(fp)
        fp.close()
        return cp
    
    def get_option(config, section, option):
        if config.has_section(section) and config.has_option(section, option):
            return config.get(section, option)
        return ''
    
    try:
        config = load_config(CONFIGURATION_FILE)
        mylocation = get_option(config, 'host', 'location')
    except:
        mylocation = ''
    
    #get hostname and IP address by getting around Mediator bug
    try:
        myhostname= socket.gethostname()
    except:
        myhostname = ''
    
    if myhostname == '':
        try:
            myaddr = socket.gethostbyname('unknown')
        except:
            myaddr = 'unknown'
    else:
        try:
            myaddr = socket.gethostbyname(myhostname)
        except:
            try:
                myaddr = socket.gethostbyname('unknown')
            except:
                myaddr = 'unknown'
    
    psp.write('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">\n')
    psp.write('<html>\n')
    psp.write('<head>\n')
    psp.write('<!-- Copyright (C) Richards-Zeta (2004). All Rights Reserved.\n\n')
    psp.write('Purpose: display Mediator hostname and IP address\n')
    psp.write('Version:\n\n')
    psp.write('$Id: mediatorname.py 20101 2011-03-06 16:02:15Z bhagn $ -->\n')
    psp.write('<title>Mediator Name</title>\n')
    psp.write('<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">\n')
    psp.write('<link href="/omega/includes/css/global.css" type="text/css" rel="stylesheet">\n')
    psp.write('<style>\n')
    psp.write('BODY {background-color: %s;}\n' % bgcolor)
    psp.write('TD {\n')
    psp.write('font-size: 9px;\n')
    psp.write('line-height: 13pt;\n')
    psp.write('font-family: %s;\n' % fontfamily)
    psp.write('color: %s;\n' % fontcolor)
    psp.write('}\n')
    psp.write('</style>\n')
    psp.write('</head>\n')
    psp.write('<body topmargin="0" leftmargin="0" marginheight="0" marginwidth="0">\n')
    psp.write('<table border="0" cellspacing="0" cellpadding="0" align="center">\n')
    if hostname == 'true':
        psp.write('<tr>\n')
        psp.write('<td class="activehardwaretd" nowrap align="right">Hostname:</td>\n')
        psp.write('<td class="activehardwaretd" nowrap align="left">%s</td>\n' % (myhostname))
        psp.write('</tr>\n')
    if ipaddress == 'true':
        psp.write('<tr>\n')
        psp.write('<td class="activehardwaretd" nowrap align="right">IP Address:</td>\n')
        psp.write('<td class="activehardwaretd" nowrap align="left">%s</td>\n' % (myaddr))
        psp.write('</tr>\n')
    if location == 'true':
        psp.write('<tr>\n')
        psp.write('<td class="activehardwaretd" nowrap align="right">Location:</td>\n')
        psp.write('<td class="activehardwaretd" align="left">%s</td>\n' % (mylocation))
        psp.write('</tr>\n')
    psp.write('</table>\n')
    psp.write('</body>\n')
    psp.write('</html>\n')
