/*
Copyright (C) 2002 2004 2005 2006 2007 2010 2011 Cisco Systems

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
**
** See WATCHDOG.txt
**
*/

/* $ID$ */

/* WAIT BUG:

/etc/rc.mfw -i

from mpx.lib import thread_pool
from mpx.lib.debug import spam
import os
def print_pids():
    print "os.getpid(): ", os.getpid()
    print "os.getppid():", os.getppid()

print_pids()
thread_pool.HIGH.queue(print_pids)
thread_pool.HIGH.queue(spam.crash)

(ps axm 2>/dev/null || ps ax) | grep /etc/rc.mfw.pyc | grep -v grep

kill-fw

*/

#include <sys/types.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <sys/statvfs.h>

#include <unistd.h>
#include <signal.h>
#include <string.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <fts.h>
#include <setjmp.h>
#include <syslog.h>

#define SYSLOGD_PID_PATH      "/var/run/syslogd.pid"

static int alarm_flag = 0;
static int usr1_flag  = 0;
static int term_flag  = 0;
static const char *program_name = "watchdog";
static const char *signaling_children = "Signaling children to exit.\n";
static const char *waiting_for_children = "Waiting for children to exit:...";
static const char *done = "done.\n";
static const char *timed_out = "timed out, terminating process group.\n";
static const char *starting_child_process = "Starting child process.\n";
static const char *forcing_recover = "Received SIGUSR1, forcing recovery.\n";
static char * const var_log_root_array[] = {
  "/var/mpx/log/msglog.log.1",
  "/var/log",
  NULL
};

static char *const *child_argv;
static char *const *child_envp;
static pid_t child_pid;
static int should_respawn = 0;
static jmp_buf respawn_stack;

typedef struct _file_system {
  char mount_point[128];
  fsblkcnt_t min_bfree;
  fsblkcnt_t min_bavail;
  fsfilcnt_t min_ffree;
  fsfilcnt_t min_favail;
  void (*handler)(const struct _file_system *fs, int force);
} file_system;

typedef struct _file_entry {
  struct _file_entry *next;
  char *szpath;
#define _FE_SIMPLEFILE 1
  unsigned long flags;
  unsigned long long size_in_bytes;
} file_entry;

typedef struct _file_list {
  unsigned long long size_in_bytes;
  unsigned long file_count;
  file_entry *first_file_entry;
} file_list;


static int exit_or_respawn_watchdog(int exit_code);

/* If system calls fail and there is no other option, call panic() to 
 * restart the framework.
 * This will not free any memory that has been malloc()'ed, so be careful when
 * you call panic().
 */
static void panic(int use_errno, const char* format, ...) {
  char       err_buf[4096];
  int        old_errno, n;
  va_list    ap;

  old_errno = errno; /* save the error number */

  sprintf(err_buf, "panic(): ");

  va_start(ap,format);
#ifdef HAVE_VSNPRINTF
  vsnprintf(err_buf,sizeof(err_buf),format,ap);
#else
  vsprintf(err_buf,format,ap);
#endif
  va_end(ap);

  if(use_errno) {
    n=strlen(err_buf);
    snprintf(err_buf+n, sizeof(err_buf)-n, ": %s", strerror(old_errno));
  }

  /* ensure buffer is NULL terminated */
  err_buf[4096-1] = '\0';

  syslog(LOG_CRIT, err_buf);

  /* restart */
  should_respawn = 1;
  exit_or_respawn_watchdog(EXIT_SUCCESS);
}

static file_list *_new_file_list(void) {
  file_list *result = malloc(sizeof(file_list));

  if (result == NULL)
    panic(1, "_new_file_list(): malloc() failed");

  memset(result, 0, sizeof *result);
  return result;
}

static file_entry *_new_entry_from_file_path(file_list *list,
					     const char *szpath) {
  file_entry *new_entry = malloc(sizeof(file_entry));

  if (new_entry == NULL)
    panic(1, "_new_entry_from_file_path(): malloc() failed");

  memset(new_entry, 0, sizeof *new_entry);
  // new_entry->size_in_bytes = f->fts_statp->st_size;
  new_entry->szpath = strdup(szpath);
  if (new_entry->szpath == NULL)
    panic(1, "_new_entry_from_file_path(): strdup() failed");
  new_entry->flags = 0;
  if (1) {
    new_entry->flags |= _FE_SIMPLEFILE;
  }
  new_entry->next = list->first_file_entry;
  return new_entry;
}

static file_entry *_new_entry(file_list *list, FTSENT *f) {
  file_entry *new_entry = malloc(sizeof(file_entry));

  if (new_entry == NULL)
    panic(1, "_new_entry(): malloc() failed");

  memset(new_entry, 0, sizeof *new_entry);
  new_entry->size_in_bytes = f->fts_statp->st_size;
  new_entry->szpath = strdup(f->fts_path);
  new_entry->flags = 0;
  if (f->fts_info & FTS_F) {
    new_entry->flags |= _FE_SIMPLEFILE;
  }
  new_entry->next = list->first_file_entry;
  return new_entry;
}

static void _del_entry(file_entry *entry) {
  if (entry) {
    free(entry->szpath);
    memset(entry, 0, sizeof(*entry));
    free(entry);
  }
  return;
}

static void _push_entry(file_list *list, file_entry *entry) {
  list->first_file_entry = entry;
  list->size_in_bytes += entry->size_in_bytes;
  list->file_count += 1;
  return;
}

static file_entry *_pop_entry(file_list *list) {
  file_entry *entry = list->first_file_entry;
  if (entry) {
    list->first_file_entry = entry->next;
    list->size_in_bytes -= entry->size_in_bytes;
    list->file_count -= 1;
    entry->next = NULL;
  }
  return entry;
}

static unsigned long long recovery_threshold = 1024L * 1024L;
file_system file_systems[16];

static void check_free_disk_space(void) {
  file_system const *fs;
  int ret;
  int i;
  struct statvfs superblock;
  for (i=0; i<sizeof(file_systems)/sizeof(file_system); i++) {
    fs = file_systems+i;
    if (fs->mount_point[0]) {
      ret = statvfs(fs->mount_point, &superblock);
      if (ret == 0) {
	if (fs->min_bfree > superblock.f_bfree ||
	    fs->min_bavail > superblock.f_bavail ||
	    fs->min_ffree > superblock.f_ffree ||
	    fs->min_favail > superblock.f_favail) {
	  fs->handler(fs, 0);
	}
      } else {
	syslog(LOG_INFO, "%s: check_free_disk_space(errno=%d,'%s')",
	       program_name, errno, strerror(errno));
      }
    }
  }
  return;
}

static void terminate_process_group(void);
static int exit_or_respawn_watchdog(int exit_code) {
  // If this process is exiting, kill all children in the same process group,
  // it's what I do.
  syslog(LOG_INFO, "In exit_or_respawn_watchdog().");
  terminate_process_group();
  if (should_respawn) {
    longjmp(respawn_stack, 1);
  }
  exit(exit_code);
  // Can't get here, but just in case...
  _exit(exit_code);
  return exit_code;
}

static void sigusr1_handler(int signum) {
  usr1_flag += 1;
  return;
}

static void force_recover_space() {
  file_system const *fs;
  int i;
  printf("%s: %s", program_name, forcing_recover);
  for (i=0; i<sizeof(file_systems)/sizeof(file_system); i++) {
    fs = file_systems+i;
    if (fs->mount_point[0]) {
      printf("%s: Recovering space on '%s'.\n", program_name, fs->mount_point);
      fs->handler(fs, 1);
    }
  }
  return;
}

static void alarm_handler(int signum) {
  /* Let the main loop know that an alarm occurred */
  alarm_flag += 1;
  return;
}

static void sigterm_handler(int signum) {
  term_flag += 1;
  return;
}

static void reset_signal_handlers(void) {
  alarm(0);
  signal(SIGUSR1, SIG_DFL);
  signal(SIGALRM, SIG_DFL);
  signal(SIGTERM, SIG_DFL);
  signal(SIGINT, SIG_DFL);
  return;
}

static void initialize_signal_handlers(void) {
  struct sigaction      sigalrm_action;

  /* Sigaction is required for SIGALRM so that an ALRM will break out of
   * a waitpid() */
  memset(&sigalrm_action, 0, sizeof(struct sigaction));
  sigalrm_action.sa_handler = &alarm_handler;
  sigaction(SIGALRM, &sigalrm_action, NULL);

  signal(SIGUSR1, sigusr1_handler);
  signal(SIGTERM, sigterm_handler);
  signal(SIGINT, SIG_IGN);
  alarm(1);
  return;
}

static int start_child_process(void) {
  pid_t oChildSid;
  int ret;
  reset_signal_handlers();
  printf("%s: %s", program_name, starting_child_process);
  child_pid = fork();
  if (child_pid == 0) {
    oChildSid = setsid();
    if (oChildSid == -1) {
      syslog(LOG_INFO, "%s: Could not establish a new process group.", program_name);
    } else {
      syslog(LOG_INFO, "Starting child with SID %d.", oChildSid);
    }
    ret = execve(child_argv[0], child_argv, child_envp);
    if (ret == -1)
	syslog(LOG_ERR, "%s execve() failed: %d - %s", 
	       program_name, errno, strerror(errno));
    /* The child should exit if the exec() call fails */
    exit(1);
  }
  syslog(LOG_INFO, "Got PID %d for child.", child_pid);
  initialize_signal_handlers();
  return child_pid;
}

static void terminate_process_group(void) {
  int i;
  int status;
  int ret;
  signal(SIGTERM, SIG_IGN);
  alarm(0);
  printf("%s: %s", program_name, signaling_children);
  printf("%s: %s", program_name, waiting_for_children);
  syslog(LOG_INFO, "Signaling child's pg (PID %d) with SIGTERM", child_pid);
  killpg(child_pid, SIGTERM);

  ret=0;
  for (i=0; i<10; i++) {
    ret = waitpid(child_pid, &status, WNOHANG);
    if (ret == -1) {
      break;
    }
    printf(".");
    fflush(stdout);
    sleep(1);
  }
  if (ret != -1) {
    printf(timed_out);
    syslog(LOG_INFO, "Got a timeout doing a waitpid() on PID %d.", child_pid);
    syslog(LOG_INFO, "Signaling child's pg (PID %d) with SIGKILL", child_pid);
    killpg(child_pid, SIGKILL);
  } else {
    printf(done);
    /*
     * Work around Python bug 756924: SIGSEGV causes hung threads (Linux).
     *
     * On MOE 2.1.x, if a thread segfaults, then waitpid(0) does not
     * include threads as processes to wait on.  Therefore, there is
     * no way to know (or is there a pthread_* call?) that there are
     * still threads running in the groups processes (and therefore
     * processes left).
     *
     * Fortunately, killpg(child_pid, SIGKILL) will kill all threads/processes
     * in the child's process group.
     */
    syslog(LOG_INFO, "Signaling child's pg (PGID %d) with SIGKILL", child_pid);
    killpg(child_pid, SIGKILL);
  }

  return;
}

static void dump_ftsent(const FTSENT *f) {
  printf("watchdog: dump_ftsent(%p):\n", f);
  printf("watchdog:   fts_cycle: %p\n", f->fts_cycle);
  printf("watchdog:   fts_parent: %p\n", f->fts_parent);
  printf("watchdog:   fts_link: %p\n", f->fts_link);
  printf("watchdog:   fts_number: %d\n", f->fts_number);
  printf("watchdog:   fts_pointer: %p\n", f->fts_pointer);
  printf("watchdog:   fts_accpath: %s\n", f->fts_accpath);
  printf("watchdog:   fts_path: %s\n", f->fts_path);
  printf("watchdog:   fts_errno: %d\n", f->fts_errno);
  printf("watchdog:   fts_symfd: %d\n", f->fts_symfd);
  printf("watchdog:   fts_pathlen: %d\n", f->fts_pathlen);
  printf("watchdog:   fts_namelen: %d\n", f->fts_namelen);
  printf("watchdog:   fts_ino: %d\n", f->fts_ino);
  printf("watchdog:   fts_dev: %d\n", f->fts_dev);
  printf("watchdog:   fts_nlink: %d\n", f->fts_nlink);
  /* #define	FTS_ROOTPARENTLEVEL	-1 */
  /* #define	FTS_ROOTLEVEL		 0 */
  printf("watchdog:   fts_level: %d\n", f->fts_level);
  /* #define	FTS_D		 1	/\* preorder directory *\/ */
  /* #define	FTS_DC		 2	/\* directory that causes cycles *\/ */
  /* #define	FTS_DEFAULT	 3	/\* none of the above *\/ */
  /* #define	FTS_DNR		 4	/\* unreadable directory *\/ */
  /* #define	FTS_DOT		 5	/\* dot or dot-dot *\/ */
  /* #define	FTS_DP		 6	/\* postorder directory *\/ */
  /* #define	FTS_ERR		 7	/\* error; errno is set *\/ */
  /* #define	FTS_F		 8	/\* regular file *\/ */
  /* #define	FTS_INIT	 9	/\* initialized only *\/ */
  /* #define	FTS_NS		10	/\* stat(2) failed *\/ */
  /* #define	FTS_NSOK	11	/\* no stat(2) requested *\/ */
  /* #define	FTS_SL		12	/\* symbolic link *\/ */
  /* #define	FTS_SLNONE	13	/\* symbolic link without target *\/ */
  /* #define FTS_W		14	/\* whiteout object *\/ */
  printf("watchdog:   fts_info: 0x%X\n", f->fts_info);
  /* #define	FTS_DONTCHDIR	 0x01 /\* don't chdir .. to the parent *\/ */
  /* #define	FTS_SYMFOLLOW	 0x02 /\* followed a symlink to get here *\/ */
  printf("watchdog:   fts_flags: 0x%X\n", f->fts_flags);
  /* #define	FTS_AGAIN	 1		/\* read node again *\/ */
  /* #define	FTS_FOLLOW	 2		/\* follow symbolic link *\/ */
  /* #define	FTS_NOINSTR	 3		/\* no instructions *\/ */
  /* #define	FTS_SKIP	 4		/\* discard node *\/ */
  printf("watchdog:   fts_instr: 0x%X\n", f->fts_instr);
  printf("watchdog:   fts_statp: %p\n", f->fts_statp);
  printf("watchdog:   fts_name: %s\n", f->fts_name);
  return;
}

static void dump_file_entry(file_entry *entry) {
  printf("watchdog: dump_file_entry(%p)\n", entry);
  printf("watchdog:   szpath=\"%s\"\n", entry->szpath);
  printf("watchdog:   size_in_bytes=%d\n", entry->size_in_bytes);
  return;
}

static file_list *create_root_disposable_list(void) {
  file_list *f_list = _new_file_list();
  file_entry *entry;
  FTS *ftsp;
  FTSENT *f;

  /* fts_open() on the mediator (2006-12-20) does not handle a list of {NULL}
   * properly.  The call to fts_read() afterwards will segfault.
   */
  if (var_log_root_array == NULL)
    return NULL;
  if (var_log_root_array[0] == NULL)
    return NULL;

  ftsp = fts_open(var_log_root_array, FTS_PHYSICAL|FTS_XDEV, NULL);
  f = fts_read(ftsp);
  while (f) {
    // dump_ftsent(f);
    entry = _new_entry(f_list, f);
    // dump_file_entry(entry);
    if (entry->flags & _FE_SIMPLEFILE) {
      _push_entry(f_list, entry);
    } else {
      // Toss the entry.
      _del_entry(entry);
    }
    f = fts_read(ftsp);
  }
  fts_close(ftsp);
  return f_list;
}

static void delete_files(file_list *f_list) {
  file_entry *entry;

  if (f_list == NULL)
      return;

  entry = f_list->first_file_entry;
  while (entry) {
    // dump_file_entry(entry);
    printf("watchdog: Deleting \"%s\"...", entry->szpath);
    if (unlink(entry->szpath) == 0) {
      printf("done.\n");
    } else {
      printf("FAILED, %s\n", strerror(errno));
    }
    entry = entry->next;
  }
  return;
}

static void delete_list(file_list *f_list) {
  file_entry *entry;

  if (f_list == NULL)
    return;

  entry = _pop_entry(f_list);
  while (entry) {
    _del_entry(entry);
    entry = _pop_entry(f_list);
  }
  free(f_list);
  return;
}

/* If the PID file for syslogd exists and is correct, send it a SIGHUP 
 * so it will continue to log after its files have been deleted. 
 */
static void prod_syslogd() {
  int syslogd_pid;
  int syslogd_fd;
  int ret;
  char syslogd_pid_buf[10] = {0};

  /* Note: printf() and syslog() are doubled up because syslogd may not be
   * available. */

  syslogd_fd = open(SYSLOGD_PID_PATH, O_RDONLY);
  if (syslogd_fd == -1) {
    printf("Could not open syslogd pid file "SYSLOGD_PID_PATH": %s\n", 
	   strerror(errno));
    syslog(LOG_INFO, "Could not open syslogd pid file "SYSLOGD_PID_PATH": %s", 
	   strerror(errno));
    return;
  }

  ret = read(syslogd_fd,syslogd_pid_buf, sizeof(syslogd_pid_buf));
  if (ret == -1) {
      printf("Could not read from syslogd pid file "SYSLOGD_PID_PATH": %s\n",
	     strerror(errno));
      syslog(LOG_INFO, 
	     "Could not read from syslogd pid file "SYSLOGD_PID_PATH": %s",
	     strerror(errno));
  }

  if (ret > 0) {
    syslogd_pid = atoi(syslogd_pid_buf);
  }

  ret = kill(syslogd_pid, SIGHUP);
  if (ret == -1) {
    printf("Could not send SIGHUP to syslogd: %s\n",
	   strerror(errno));
    syslog(LOG_INFO, "Could not send SIGHUP to syslogd: %s\n",
	   strerror(errno));
  }

  close(syslogd_fd);
}

static void recover_root_space(const struct _file_system *fs, int force) {
  static int busy = 0;
  file_list *disposable_files;
  if (!busy++) {
    disposable_files = create_root_disposable_list();
    if (disposable_files == NULL)
      return;
    if (force || disposable_files->size_in_bytes >= recovery_threshold) {
      terminate_process_group();
      delete_files(disposable_files);
      start_child_process();
    }
    delete_list(disposable_files);
  }
  busy--;
  prod_syslogd();
  return;
}

static char *const *init_watchdog(int argc, char *const argv[]) {
  // Right now, always check the filesystem mounted at '/'.
  int child_argv_offset = 1;
  strcpy(file_systems[0].mount_point, "/");
  file_systems[0].min_bfree = 1;
  file_systems[0].min_bavail = 1;
  file_systems[0].min_ffree = 1;
  file_systems[0].min_favail = 1;
  file_systems[0].handler = recover_root_space;
  if (strcmp(argv[child_argv_offset],"--respawn") == 0) {
    should_respawn=1;
    child_argv_offset+=1;
  }
  return argv+child_argv_offset ;
}

int main(int argc, char *const argv[], char *const envp[]) {
  pid_t saved_pid;
  int status;
  int ret;

  if (argc < 3)
    syslog(LOG_INFO,"Insufficient number of arguments (%d).", argc - 1);

  child_envp = envp;
  child_argv = init_watchdog(argc, argv);

  openlog("MpxWatchdog", LOG_CONS | LOG_NDELAY | LOG_PID, LOG_DAEMON);
  
  syslog(LOG_INFO, "Started framework watchdog version 1.1.");

  ret = setjmp(respawn_stack);
  if (ret) {
    printf("%s: Respawning child.\n", program_name);
    syslog(LOG_INFO, "Respawning child");
  }

  saved_pid = start_child_process();
  while (1) {
    alarm_flag = 0;
    usr1_flag = 0;
    ret = waitpid(child_pid, &status, 0);
    if (ret == -1) {
      /* Check if waitpid() was interrupted by a signal */
      if (errno == EINTR) {
	if (alarm_flag) {
	  check_free_disk_space();
	  alarm(1);
	}
	if (usr1_flag) {
	  force_recover_space();
	}
	if (term_flag) {
	  term_flag = 0;
	  should_respawn = 0;
	  exit_or_respawn_watchdog(EXIT_FAILURE);
	  /* Does not continue execution from here */
	}

	if (alarm_flag || usr1_flag)
	    continue;

      }
      if (errno == ECHILD) {
	if (saved_pid != child_pid) {
	  // The child was restarted, go wait on the new child.
	  saved_pid = child_pid;
	  continue;
	}
      }
    }
    // Child exited or an unhandled error condition occurred, give up.
    break;
  }

  /* Log some info about how the process exited */
  if (WIFEXITED(status))
    syslog(LOG_INFO, "Child process exited normally, returned %d",
	   WEXITSTATUS(status));

  else if (WIFSIGNALED(status))
    syslog(LOG_INFO, "Child process terminated after catching a signal (%d)",
	   WTERMSIG(status));

  else
    syslog(LOG_INFO, "Child process exited; status did not match WIFEXITED "
	   "or WIFSIGNALED");
  
  // Prepare for dog heaven and take all our puppies with us.
  return exit_or_respawn_watchdog(EXIT_SUCCESS);
}
