"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
#encoding: UTF-8
# Start Mediator Framework.

from tools.lib import DecodeStatus

def print_help():
    print """\nrc.mfw [-i] [-x xml_file]

    Start the Mediator Framework running, loading its configuration from an
    XML file.

    -i    Run in interactive debug mode.

    -p    Load Psyco globally.

    -x xml_config
          Specify the XML file to read Broadway's configuration.  If this
          option is not specified, then the default Broadway configuration
          file is used ('/var/mpx/config/broadway.xml').
    """

def load_config(filename):
    import ConfigParser
    cp = ConfigParser.ConfigParser()
    try:
        fp = open(filename, 'r')
        cp.readfp(fp)
        fp.close()
    except:
        pass
    return cp

def MAIN(argv):
    interactive_debug = 0
    config_file = None

    # Parse the command line to modify the default behavior.
    # THIS IS DONE BEFORE MOST IMPORTS TO HELP PSYCO (I think).
    # @fixme cleanup, maybe move to part of mpx.system.run(argv)
    state = 'seek'
    for i in range(1,len(argv)):
        arg = argv[i]
        if state == 'seek':
            if arg == '-i':
                interactive_debug = 1
            elif arg == '-p':
                import psyco
                psyco.full()
            elif arg == '-x':
                state = 'config'
            else:
                print_help()
                raise SystemExit
        elif state == 'config':
            config_file = arg
            state = 'seek'
        else:
            print_help()
            raise SystemExit

    import os
    from mpx import properties
    from mpx.system import run
    from mpx.lib import msglog

    try:
        init_config = load_config(properties.MPXINIT_CONF_FILE)
        if 'proxyserver' in dict(init_config.items('host')).keys():
            proxy = str(dict(init_config.items('host'))['proxyserver']).strip()
            if len(proxy) and proxy != '0.0.0.0':
                if not proxy.startswith('http://'):
                    proxy = 'http://' + proxy
                import urllib2
                os.environ['http_proxy'] = proxy
                urllib2.ProxyHandler()
    except:
        pass

    # Technically, these should be properties, but it's not imperative.
    # Why? For one, these files are very specialized and not referenced outside
    # of here and Mpxconfig. Secondly, this script only checks for the exitance
    # of the files, and does nothing if they don't exist, so there should be
    # no impact if run outside of a genuine mediator environment.  It's another
    # matter, however, if the framework is ported to another operating system.
    HOST_NAME_CHANGED_FILE = '/etc/mpx_hostnamechanged.tmp'
    TIME_CHANGED_FILE = '/etc/mpx_timechanged.tmp'
    CERTIFICATE_FILE = '/usr/lib/broadway/http/certificate.pem'

    # Delete the web certificate if the host name has changed, as indicated by
    # tmp file left behind by Mpxconfig.
    if os.path.exists(HOST_NAME_CHANGED_FILE):
        os.remove(HOST_NAME_CHANGED_FILE)
        if os.path.exists(CERTIFICATE_FILE):
            os.remove(CERTIFICATE_FILE)
        
    # Delete the web certificate if the time has changed, as indicated by
    # tmp file left behind by Mpxconfig.
    if os.path.exists(TIME_CHANGED_FILE):
        os.remove(TIME_CHANGED_FILE)
        if os.path.exists(CERTIFICATE_FILE):
            os.remove(CERTIFICATE_FILE)
    
    if config_file is None:
        config_file = properties.CONFIGURATION_FILE
    
    # Perform any indicated SRNA CA/certs/keys updates:
    from tools.srna.update_srna_local import update_srna
    update_srna()

    #check if root user exists, and if so, delete that user
    flag=0
    x=open("/etc/passwd")
    for line in x.readlines():
        if line[:5]=="root:":
            flag=1
    x.close()

    # Removing root entry from /etc/passwd and /etc/shadow breaks system utilities
    # like cron that expect the entry to exist.
    # So this code is disabled by forcing flag to be zero for now.
    # Making the Framework run as a non root user might help clean this up too.
    # @fixme mpxadmin user is effectively root user anyway so there is not much point in removing root
    flag = 0

    if(flag==1):
        msglog.log('rc.mfw', msglog.types.WARN,
                   'Root account detected. Deleting root account')
        from tempfile import mkstemp
        fd,temp_path_pass=mkstemp(dir='/etc/')
        o=open('/etc/passwd','r')
        for line in o.readlines():
            if line[:5] != 'root:':
                os.write(fd,line)
        o.close()
        os.close(fd)
        
        fd,temp_path_sh=mkstemp(dir='/etc/')
        o=open('/etc/shadow','r')
        for line in o.readlines():
            if line[:5] != 'root:':
                os.write(fd,line)
        o.close()
        os.close(fd)
        
        #the following two commands should ideally be one atomic operation
        #os.rename is guaranteed atomic on linux. If context switch happens 
        #after one rename, all is not lost. shadow file must contain a line 
        #for every user in passwd, but extra lines will not affect operation
        os.rename(temp_path_pass,'/etc/passwd')
        os.rename(temp_path_sh,'/etc/shadow')
        
        
    # 'Bootstrap' the Mediator framework.
    # @fixme move a bunch of this into the Framework.
    msglog.log('rc.mfw', msglog.types.INFO,
               'Loading Broadway, the Mediator Framework from %s.' %
               config_file)
    if interactive_debug:
        msglog.log('rc.mfw', msglog.types.WARN,
                   'Framework is starting in interactive debug mode.')
        run(config_file, interactive_debug)
    else:
        try:
            run(config_file, interactive_debug)
        except SystemExit, e:
            if e.args:
                args = (e.code,) + e.args
            else:
                args = "(%s)" % e.code
            log_message('rc.mfw', msglog.types.WARN,
                        'Framework is exiting due to a SystemExit%s.' % args)
            raise e
        except Exception, e:
            msglog.exception()
            raise e
        except:
            msglog.exception()
            raise "Framework is exiting due to an unknown exception."

if __name__ == '__main__':
    from sys import argv as _argv
    MAIN(_argv)
