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
    psp.write("<html>\n")
    psp.write("<head>\n")
    psp.write("<!-- $Name: mediator_3_1_2_branch $ -->\n")
    psp.write("<!-- $Id: mediatorconfig.py 20101 2011-03-06 16:02:15Z bhagn $ -->\n")
    psp.write("<style>\n")
    psp.write("BODY {\n")
    psp.write("    font-family: Verdana, Arial, Helvetica, sans-serif;\n")
    psp.write("    font-size: 11px;\n")
    psp.write("    color: #000000;\n")
    psp.write("	line-height: 17pt;\n")
    psp.write("}\n")
    psp.write("\n")
    psp.write("DIV {\n")
    psp.write("    font-family: Verdana, Arial, Helvetica, sans-serif;\n")
    psp.write("    font-size: 11px;\n")
    psp.write("    color: #000000;\n")
    psp.write("	line-height: 17pt;\n")
    psp.write("}\n")
    psp.write("\n")
    psp.write("TD {\n")
    psp.write("    font-family: Verdana, Arial, Helvetica, sans-serif;\n")
    psp.write("    font-size: 11px;\n")
    psp.write("    line-height: 17pt;\n")
    psp.write("}\n")
    psp.write("\n")
    psp.write(".normal{\n")
    psp.write("color:#555555;\n")
    psp.write("}\n")
    psp.write("\n")
    psp.write(".error{\n")
    psp.write("color:#FF0000;\n")
    psp.write("}\n")
    psp.write("\n")
    psp.write("</style>\n")
    psp.write("</head>\n")
    psp.write("<body>\n")
    import os
    import sys
    from mpx.lib import ifconfig
    from mpx.lib.http import MultipartCollector
    from mpx import properties
    import ConfigParser
    
    CONFIGURATION_FILE = os.path.join(properties.ETC_DIR, 'mpxinit.conf')
    
    if request.get_protocol() == 'http':
        root = properties.HTTP_ROOT
    else:
        root = properties.HTTPS_ROOT
    
    m = MultipartCollector(request)
    mkeys = m.keys()
    dir_list =[]
    local_file = ''
    filename =''
    dir = ''
    web_dir_class = 'normal'
    local_file_class = 'normal'
    filename_class = 'normal'
    display_form = 0
    
    def load_config(filename):
        cp = ConfigParser.ConfigParser()
        try:
            fp = open(filename, 'r')
            cp.readfp(fp)
            fp.close()
        except:
            pass
        return cp
    
    def get_option(config, section, option):
        if config.has_section(section) and config.has_option(section, option):
            return config.get(section, option)
        return ''
    
    def doChanges(config):
        if 'host_location' in mkeys:
            config.set('host', 'location', m['host_location'].value)
        if 'host_hostname' in mkeys:
            config.set('host', 'hostname', m['host_hostname'].value)
        if 'host_domain_name' in mkeys:
            config.set('host', 'domain_name', m['host_domain_name'].value)
        if 'host_gateway' in mkeys:
            config.set('host', 'gateway', m['host_gateway'].value)
        if 'host_nameserver' in mkeys:
            config.set('host', 'nameserver', m['host_nameserver'].value)
        if 'host_proxyserver' in mkeys:
            config.set('host', 'proxyserver', m['host_proxyserver'].value)
        if 'eth0_dhcp' in mkeys:
            config.set('eth0', 'dhcp', m['eth0_dhcp'].value)
        if 'eth1_dhcp' in mkeys:
            config.set('eth1', 'dhcp', m['eth1_dhcp'].value)
        if 'eth0_ip_addr' in mkeys:
            config.set('eth0', 'ip_addr', m['eth0_ip_addr'].value)
        if 'eth1_ip_addr' in mkeys:
            config.set('eth1', 'ip_addr', m['eth1_ip_addr'].value)
        if 'eth0_netmask' in mkeys:
            config.set('eth0', 'netmask', m['eth0_netmask'].value)
        if 'eth1_netmask' in mkeys:
            config.set('eth1', 'netmask', m['eth1_netmask'].value)
    
    def doSave():
        psp.write('Saving Configuration...')
        try:
            cp = ConfigParser.ConfigParser()
            fp = open(os.path.join(properties.ETC_DIR, 'mpxinit.conf'), 'r')
            cp.readfp(fp)
            fp.close()
            wp = open(os.path.join(properties.ETC_DIR, 'mpxinit.old'),'w')
            cp.write(wp)
            wp.close()
            doChanges(cp)
            fp = open(os.path.join(properties.ETC_DIR, 'mpxinit.conf'), 'w')
            cp.write(fp)
            fp.close()
        except Exception,e:
            psp.write('ERROR:%s<br>' % e)
            return -1
        else:
            psp.write('Done<br>')
            return 0
    
    def doReboot():
        psp.write('Rebooting...<br>')
        os.system('(sleep 2; /sbin/reboot -f) &')
    
    def macAddr(adapter):
        try:
            return ifconfig.mac_address('eth%d' % adapter)
        except:
            pass
        return ''
    
    if mkeys == []:
        display_form = 1
    
    if 'save' in mkeys:
        retval = doSave()
    if 'savereboot' in mkeys:
        retval = doSave()
        if retval == 0:
            doReboot()
    if 'reboot' in mkeys:
        doReboot()
    if 'refresh' in mkeys:
        display_form = 1
    
    if display_form:
        config = load_config(CONFIGURATION_FILE)
        #host_location
        #host_hostname
        #host_domain_name
        #host_gateway
        #host_nameserver
        #host_proxyserver
        rawomegasoftvers = '$Name: mediator_3_1_2_branch $'
        colonindex = rawomegasoftvers.index(':')
        #omegasoftvers = rawomegasoftvers[colonindex + 1:].replace('$','').strip()
        omegasoftvers = 'Omega 2.2'
        eth0_dhcp = get_option(config, 'eth0', 'dhcp')
        eth1_dhcp = get_option(config, 'eth1', 'dhcp')
        psp.write("    <form action=\"/webapi/psp/mediatorconfig.psp\" method=\"post\" enctype=\"multipart/form-data\" name=\"mediatorconfig\" >\n")
        psp.write("    <table width=\"100%\" border=\"0\" cellspacing=\"0\" cellpadding=\"2\" align=\"center\" valign=\"middle\"  >\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" nowrap>Model:&nbsp;&nbsp;</td>\n")
        psp.write("    <td><input name=\"model\" type=\"text\" size=\"20\" maxlength=\"20\" readonly=\"true\" value=\"" + str(properties.HARDWARE_CLASS) + "\"></td>\n")
        psp.write("    <td align=\"right\" nowrap>Serial Number:&nbsp;&nbsp;</td>\n")
        psp.write("    <td><input name=\"serialnumber\" type=\"text\" size=\"20\" maxlength=\"20\" readonly=\"true\" value=\"" + str(properties.SERIAL_NUMBER) + "\"></td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" nowrap>MOE Version:&nbsp;&nbsp;</td>\n")
        psp.write("    <td><input name=\"moeversion\" type=\"text\" size=\"20\" maxlength=\"20\" readonly=\"true\" value=\"" + str(properties.MOE_VERSION) + "\"></td>\n")
        psp.write("    <td align=\"right\" nowrap>Framework Version:&nbsp;&nbsp;</td>\n")
        psp.write("    <td><input name=\"frameworkversion\" type=\"text\" size=\"20\" maxlength=\"20\" readonly=\"true\" value=\"" + str(properties.COMPOUND_VERSION) + "\"></td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" colspan=\"1\" nowrap>Omega Version:&nbsp;&nbsp;</td>\n")
        psp.write("    <td align=\"left\" colspan=\"3\" nowrap>\n")
        psp.write("    <input name=\"omegaversion\" type=\"text\" size=\"60\" maxlength=\"60\" value=\"" + str(omegasoftvers) + "\">\n")
        psp.write("    </td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" nowrap>Location:&nbsp;&nbsp;</td>\n")
        psp.write("    <td colspan=\"3\"><input name=\"host_location\" type=\"text\" size=\"60\" maxlength=\"60\" value=\"" + str(get_option(config, 'host', 'location')) + "\"></td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" colspan=\"1\" nowrap>Hostname:&nbsp;&nbsp;</td>\n")
        psp.write("    <td align=\"left\" colspan=\"3\" nowrap>\n")
        psp.write("    <input name=\"host_hostname\" type=\"text\" size=\"60\" maxlength=\"60\" value=\"" + str(get_option(config, 'host', 'hostname')) + "\">\n")
        psp.write("    </td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" colspan=\"1\" nowrap>Domain Name:&nbsp;&nbsp;</td>\n")
        psp.write("    <td align=\"left\" colspan=\"3\" nowrap>\n")
        psp.write("    <input name=\"host_domain_name\" type=\"text\" size=\"60\" maxlength=\"60\" value=\"" + str(get_option(config, 'host', 'domain_name')) + "\">\n")
        psp.write("    </td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" colspan=\"1\" nowrap>Gateway:&nbsp;&nbsp;</td>\n")
        psp.write("    <td align=\"left\" colspan=\"3\" nowrap>\n")
        psp.write("    <input name=\"host_gateway\" type=\"text\" size=\"60\" maxlength=\"60\" value=\"" + str(get_option(config, 'host', 'gateway')) + "\">\n")
        psp.write("    </td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" colspan=\"1\" nowrap>Name Server:&nbsp;&nbsp;</td>\n")
        psp.write("    <td align=\"left\" colspan=\"3\" nowrap>\n")
        psp.write("    <input name=\"host_nameserver\" type=\"text\" size=\"60\" maxlength=\"60\" value=\"" + str(get_option(config, 'host', 'nameserver')) + "\">\n")
        psp.write("    </td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" colspan=\"1\" nowrap>Proxy Server:&nbsp;&nbsp;</td>\n")
        psp.write("    <td align=\"left\" colspan=\"3\" nowrap>\n")
        psp.write("    <input name=\"host_proxyserver\" type=\"text\" size=\"60\" maxlength=\"60\" value=\"" + str(get_option(config, 'host', 'proxyserver')) + "\">\n")
        psp.write("    </td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td colspan=\"1\" nowrap>&nbsp;</td>\n")
        psp.write("    <td align=\"center\" colspan=\"1\" nowrap>Ethernet 0</td>\n")
        psp.write("    <td align=\"center\" colspan=\"1\" nowrap>Ethernet 1</td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" colspan=\"1\" nowrap>MAC Address:&nbsp;&nbsp;</td>\n")
        psp.write("    <td align=\"center\" colspan=\"1\" nowrap>\n")
        psp.write("    <input name=\"macaddr0\" type=\"text\" size=\"20\" maxlength=\"20\" readonly=\"true\" value=\"" + str(macAddr(0)) + "\">\n")
        psp.write("    </td>\n")
        psp.write("    <td align=\"center\" colspan=\"1\" nowrap>\n")
        psp.write("    <input name=\"macaddr1\" type=\"text\" size=\"20\" maxlength=\"20\" readonly=\"true\" value=\"" + str(macAddr(1)) + "\">\n")
        psp.write("    </td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" colspan=\"1\" nowrap>DHCP:&nbsp;&nbsp;</td>\n")
        psp.write("    <td align=\"center\" colspan=\"1\" nowrap>\n")
        psp.write("    <select name=\"eth0_dhcp\" size=\"1\">\n")
        if eth0_dhcp == 'disabled':
            psp.write('<option value="disabled" selected>disabled</option>\n')
            psp.write('<option value="enabled">enabled</option>\n')
        else:
            psp.write('<option value="disabled">disabled</option>\n')
            psp.write('<option value="enabled" selected>enabled</option>\n')
        psp.write("    </select>\n")
        psp.write("    </td>\n")
        psp.write("    <td align=\"center\" colspan=\"1\" nowrap>\n")
        psp.write("    <select name=\"eth1_dhcp\" size=\"1\">\n")
        if eth1_dhcp == 'disabled':
            psp.write('<option value="disabled" selected>disabled</option>\n')
            psp.write('<option value="enabled">enabled</option>\n')
        else:
            psp.write('<option value="disabled">disabled</option>\n')
            psp.write('<option value="enabled" selected>enabled</option>\n')
        psp.write("    </select>\n")
        psp.write("    </td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" colspan=\"1\" nowrap>IP Address:&nbsp;&nbsp;</td>\n")
        psp.write("    <td align=\"center\" colspan=\"1\" nowrap>\n")
        psp.write("    <input name=\"eth0_ip_addr\" type=\"text\" size=\"20\" maxlength=\"20\" value=\"" + str(get_option(config, 'eth0', 'ip_addr')) + "\">\n")
        psp.write("    </td>\n")
        psp.write("    <td align=\"center\" colspan=\"1\" nowrap>\n")
        psp.write("    <input name=\"eth1_ip_addr\" type=\"text\" size=\"20\" maxlength=\"20\" value=\"" + str(get_option(config, 'eth1', 'ip_addr')) + "\">\n")
        psp.write("    </td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"right\" colspan=\"1\" nowrap>IP Netmask:&nbsp;&nbsp;</td>\n")
        psp.write("    <td align=\"center\" colspan=\"1\" nowrap>\n")
        psp.write("    <input name=\"eth0_netmask\" type=\"text\" size=\"20\" maxlength=\"20\" value=\"" + str(get_option(config, 'eth0', 'netmask')) + "\">\n")
        psp.write("    </td>\n")
        psp.write("    <td align=\"center\" colspan=\"1\" nowrap>\n")
        psp.write("    <input name=\"eth1_netmask\" type=\"text\" size=\"20\" maxlength=\"20\" value=\"" + str(get_option(config, 'eth1', 'netmask')) + "\">\n")
        psp.write("    </td>\n")
        psp.write("    </tr>\n")
        psp.write("    <tr>\n")
        psp.write("    <td align=\"center\"><input name=\"save\" type=\"submit\" value=\"Save\"></td>\n")
        psp.write("    <td align=\"center\"><input name=\"savereboot\" type=\"submit\" value=\"Save/Reboot\"></td>\n")
        psp.write("    <td align=\"center\"><input name=\"reboot\" type=\"submit\" value=\"Reboot\"></td>\n")
        psp.write("    <td align=\"center\"><input name=\"refresh\" type=\"submit\" value=\"Refresh\"></td>\n")
        psp.write("    </tr>\n")
        psp.write("    </table>\n")
        psp.write("    </form>\n")
        psp.write("\n")
    psp.write("<script type=\"text/javascript\">\n")
    psp.write("\n")
    psp.write("function get_filename(path){\n")
    psp.write("  var f = '';\n")
    psp.write("  var len = path.length;\n")
    psp.write("  while (len != 0){\n")
    psp.write("    var c = path.substring(len-1,len);\n")
    psp.write("    if (c == '/' || c ==':'|| c=='\\\\'){\n")
    psp.write("       f = path.substring(len,path.length);       \n")
    psp.write("       len = 0     \n")
    psp.write("     }       \n")
    psp.write("     else{\n")
    psp.write("       len--;\n")
    psp.write("     }\n")
    psp.write("  }\n")
    psp.write("  return f\n")
    psp.write("}\n")
    psp.write("\n")
    psp.write("function update_filename(){\n")
    psp.write("  var uploadfile = document.getElementById(\"uploadfile\").value;\n")
    psp.write("  if(uploadfile.length > 25){\n")
    psp.write("    document.getElementById(\"uploadfile\").size = uploadfile.length;\n")
    psp.write("  }\n")
    psp.write("  else{\n")
    psp.write("    document.getElementById(\"uploadfile\").size = 25;\n")
    psp.write("  }  \n")
    psp.write("  var fn = get_filename(uploadfile);\n")
    psp.write("  if(fn.length > 25){\n")
    psp.write("    document.getElementById(\"filename\").size = fn.length;\n")
    psp.write("  }\n")
    psp.write("  else{\n")
    psp.write("    document.getElementById(\"filename\").size = 25;\n")
    psp.write("  }\n")
    psp.write("  document.getElementById(\"filename\").value = get_filename(uploadfile);  \n")
    psp.write("}\n")
    psp.write("\n")
    psp.write("</script>\n")
    psp.write("</body>\n")
    psp.write("</html>\n")
    psp.write("\n")
