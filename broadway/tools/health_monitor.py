"""
Copyright (C) 2011 Cisco Systems

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
import subprocess
import time
import logging
import os
import sys
import signal
import ConfigParser
from logging import handlers
from logging import Formatter
import mpx
from mpx.lib.daemon.daemon1 import Daemon

class health_monitor(Daemon) :
    def __init__(self):
        self._logger_init()
        pidfile=mpx.properties.VAR_RUN_BROADWAY+'/'+'health_monitor.pid'
        Daemon.__init__(self, pidfile)

    def read_config(self):
        config = ConfigParser.ConfigParser()
        self.config=config
        conf_dir=mpx.properties.CONFIGURATION_DIR
        cfg_file=conf_dir+'/'+'health_monitor.cfg'
        config.read(cfg_file)
        ph=self.read_value('user','ping_hosts','')
        if(ph == ''):
            self.ping_hosts=[]
        else:
            self.ping_hosts=(''.join(ph.split())).split(',')
        self.ping_count=self.read_value('user','ping_count',5)
        self.monitor_period=self.read_value('user','monitor_period',300)
        self.logger.info('ping_hosts=%s ping_count=%s monitor_period=%s ' %(self.ping_hosts,self.ping_count,self.monitor_period))

    def read_value(self,section_name,option,default_value):
        try:
            if(type(default_value) == str):
                value=self.config.get(section_name,option)
            elif(type(default_value) == int):
                value=self.config.getint(section_name,option)
            else:
                value=self.config.getfloat(section_name,option)
        except :
            value=default_value
        return(value)

    def _run_cmd(self,cmd):
        p = subprocess.Popen(cmd, shell=True, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out,err)=p.communicate()
        return(p.returncode,out)

    def memory_usage(self):
        cmd='top -b -n 1'
        (ret,out)=self._run_cmd(cmd)
        self.logger.info('Memory and CPU Usage information \n'+out)

    def _logger_init(self):
        log_dir=mpx.properties.LOGFILE_DIRECTORY
        log_path = log_dir+'/'+'health_monitor.log'
        logger=logging.getLogger('HealthMonitor')
        handler = handlers.TimedRotatingFileHandler(log_path,when='midnight',interval=1,backupCount=4)
        log_format = Formatter("%(name)s %(asctime)s %(levelname)s : %(message)s")
        handler.setFormatter(log_format)
        logger.addHandler(handler)
        ## set the root logging level
        logger.setLevel(logging.DEBUG)
        self.logger=logger

    def _test_logs(self):
        for i in range(11000):
            ## write test logging
            self.logger.debug('debug')
            self.logger.info('info')
            self.logger.warning('warning')
            self.logger.critical('critical')
            self.logger.error('error')
            self.logger.fatal('fatal')

    def cpu_usage(self):
        pass

    def nw_status(self):
        cmd='ifconfig -a '
        (ret,out)=self._run_cmd(cmd)
        self.logger.info('Network related Information \n'+out)

    def nw_connectivity(self):
        hosts=self.ping_hosts
        ping_count=self.ping_count
        for host in hosts:
            cmd='ping -W 5 -c ' + str(ping_count) +' '+ host
            (ret,out)=self._run_cmd(cmd)
            self.logger.info('Ping Information to the host %s \n%s' %(host,out))

    def failed_ssh_attempts(self):
        cmd='grep -i failed /var/log/messages | grep -i sshd'
        cmd1='grep -i failed '
        path_found = False
        for line in open('/etc/syslog.conf').readlines():
            if 'authpriv.*' in line:
                items = line.split()
                key = items[0].strip()
                if key.startswith('#'):
                  continue
                value = items[1].strip()
                cmd1 = cmd1 + value + ' | grep -i sshd'
                path_found = True
                break
        if path_found:
          (ret,out)=self._run_cmd(cmd1)
        else:
          (ret,out)=self._run_cmd(cmd)
        self.logger.info('Failed SSH login attempts \n'+out)


    def main(self):
        self.memory_usage()
        self.cpu_usage()
        self.nw_status()
        self.nw_connectivity()
        self.failed_ssh_attempts()
        #self._test_logs()

    def run(self):
        self.read_config()
        monitor_period=self.monitor_period
        while(True):
            self.main()
            time.sleep(monitor_period)

if __name__ == "__main__":
    daemon = health_monitor()
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        script = sys.argv[0]
        s = script.split('.')
        print "usage: %s start|stop|restart" % s[0]
        sys.exit(2)
