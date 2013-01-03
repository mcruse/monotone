/*
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
*/
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <signal.h>
#include <errno.h>
#include <getopt.h>
#include <linux/fs.h>
#include <linux/types.h>
#include <asm/types.h>
#include <linux/watchdog.h>
#include <libgen.h>
#include <syslog.h>

#define WDT "/dev/wdt"

#define LOCKFILE "/var/run/watchdog.pid"

#define OK 0
#define FAILED -1

#define MAJOR_NUM 1
#define MINOR_NUM 0

char *progname = NULL;

int watchdog = -1;

void terminate(int signo)
{
    if (watchdog != -1) {
        /*
         * "V" is the magic close character that tells the kernel wdt module
         * that we want the watchdog disabled.
        */
        if (write(watchdog, "V", 1) < 0) {
            int err = errno;
            syslog(LOG_ERR, "write watchdog device gave error %d = '%m' in terminate()!", err);
        }
        if (close(watchdog) < 0) {
            syslog(LOG_ERR, "cannot close %s (errno = %d)", WDT, errno);
        } else {
            syslog(LOG_INFO, "disabling the hardware wdt");
        }
    }
    unlink(LOCKFILE);
    exit(OK);
}

void go_daemon(void)
{
    FILE *f_lock;
    pid_t pid;
    /*
     * Fork process and detatch
     */
    if ((pid = fork()) > 0) {
        f_lock = fopen(LOCKFILE, "w");
        fprintf(f_lock, "%d", pid);
        fclose(f_lock);
        exit(OK);
    }
    else if(pid < 0) {
        perror("fork");
        fprintf(stderr,"%s: could not start daemon\n", progname);
        exit(FAILED);
    }
    if(setsid() < 0) {
        perror("setsid");
        fprintf(stderr, "%s: could not start daemon\n", progname);
        exit(FAILED);
    }

    /* Ignore unneeded signals */
    signal(SIGTTOU, SIG_IGN);
    signal(SIGTTIN, SIG_IGN);
    signal(SIGCHLD, SIG_IGN);
    signal(SIGHUP, SIG_IGN);
    signal(SIGINT, SIG_IGN);
    signal(SIGQUIT, SIG_IGN);
    signal(SIGTSTP, SIG_IGN);
    signal(SIGUSR1, SIG_IGN);
    signal(SIGUSR2, SIG_IGN);
    /*
     * Call terminate() on the following signals so that the
     * watchdog device is closed properly.
    */
    signal(SIGTERM, terminate);
    signal(SIGKILL, terminate);
    /* Close all unneeded file descriptors */
    close(0);
    close(1);
    close(2);

    chdir("/");
    umask(0);
}

int kill_daemon(void)
{
    FILE *f_lock;
    pid_t pid;

    if((f_lock = fopen(LOCKFILE, "r")) == NULL) {
        fprintf(stderr,"cannot find %s\n", LOCKFILE);
        return FAILED;
    }

    if(fscanf(f_lock, "%d", &pid) < 1) {
        fprintf(stderr, "cannot read %s\n", LOCKFILE);
        return FAILED;
    }

    if(kill(pid, SIGTERM) < 0) {
        perror("process");
        return FAILED;
    }
    return OK;
}

int is_running(void)
{
    FILE *f_lock;
    if((f_lock = fopen(LOCKFILE, "r")) == NULL) {
        return 0;
    }
    fclose(f_lock);
    return 1;
}

void help(char **argv)
{
  printf("Usage: %s [-khv]\n\
        -k, --kill      : kill running %s process\n\
        -h, --help      : this help screen\n\
        -t, --timeout   : set the wdt timeout\n", argv[0], argv[0]);
}

int main(int argc, char *argv[])
{
    int curopt;
    int wdt_timeout = 30;
    int needs_restart = 0;
    struct option opts[] =
    {
        {"help", no_argument, NULL, 'h'},
        {"restart", no_argument, NULL, 'r'},
        {"kill", no_argument, NULL, 'k'},
        {"timeout", required_argument, NULL, 't'},
        {NULL, 0, NULL, 0}
    };
    progname = basename(argv[0]);
    while ((curopt = getopt_long(argc, argv, "hrkt:", opts, NULL)) != EOF) {
        switch(curopt) {
            case 'h':
                help(argv);
                exit(OK);
            case 'k':
                if(!is_running()) {
                    fprintf(stderr, "%s: the watchdog driver is not running\n", argv[0]);
                    exit(FAILED);
                }
                if(kill_daemon() < 0) {
                    fprintf(stderr, "%s: could not kill the watchdog driver\n", argv[0]);
                    exit(FAILED);
                }
                printf("%s: watchdog driver successfully unloaded\n", argv[0]);
                exit(OK);
            case 'r':
                if(is_running()) {
                    if(kill_daemon() < 0) {
                        fprintf(stderr, "%s: could not restart the watchdog driver\n", argv[0]);
                        exit(FAILED);
                    }
                }
                needs_restart = 0;
                break;
            case 't':
                wdt_timeout = (int)strtol(optarg, (char**)NULL, 10);
                /* if the daemon is already running, it will need to
                 * to be restarted for the timeout change to take effect
                 */
                needs_restart = is_running();
                break;
            case '?':
                help(argv);
                exit(OK);
            default:
                break;
        }
    }
    if(optind != argc) {
        /* extra (invalid) args passed */
        fprintf(stderr,"%s: Illegal option -- %s\n",argv[0], argv[optind]);
        help(argv);
        exit(FAILED);
    }

    if(needs_restart) {
        /* timeout changed - force a restart */
        if(kill_daemon() < 0) {
            fprintf(stderr, "%s: could not restart daemon\n", argv[0]);
            exit(FAILED);
        }
        needs_restart = 0;
    }

    /*
     * An open failure means that /dev/wdt is already open (which means
     * that some timer already has control of it).
    */
    if ((watchdog = open(WDT, O_WRONLY)) < 0){
        fprintf(stderr,"%s: could not open %s.  Daemon may already be running\n",
            argv[0], WDT);
        exit(FAILED);
    }

    go_daemon();

    /* Start logging */
    openlog(progname, LOG_PID, LOG_DAEMON);
    syslog(LOG_INFO, "starting wdt keepalive daemon (%d.%d):", MAJOR_NUM, MINOR_NUM);

    ioctl(watchdog, WDIOC_SETTIMEOUT, &wdt_timeout);
    syslog(LOG_INFO, "setting the wdt timeout to %d seconds", wdt_timeout);
    /*
     * Now just start the timer and keep it running
     */
    while(1) {
        if (write(watchdog, "\0", 1) < 0) {
            int err = errno;
            syslog(LOG_ERR, "write watchdog device gave error %d = '%m'!", err);
        }
        sleep(wdt_timeout / 3);
    }
}

