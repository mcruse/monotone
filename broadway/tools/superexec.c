/*
Copyright (C) 2002 2010 2011 Cisco Systems

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
 *  Python threads are created with all signals blocked so that only the  main
 *  thread can be signalled.   Processes launched from Python threads  inherit
 *  the signal properties,  so they will also have all their signals  blocked.
 *  This is not always desireable.   This program works around  the  issue  by
 *  acting as a process launcher that can be invoked from a Python thread. All
 *  signals are unblocked before launching the specifed process.
 */
#include <sys/types.h>
#include <signal.h>
#include <unistd.h>
#include <stdio.h>

/*
 *  safe_exec
 *
 *  Execute the specified file, replacing the current process.
 *  All signals are unblocked prior to execution.
 *
 *  Parameters:
 *    pFilePath   - string specifying the file to execute
 *    argv        - the argument vector passed to new process;
 *                  the first argument should be the command name.
 *
 *  Returns:
 *    Does not return if successful, otherwise 255 is returned.
 */
static
int safe_exec( const char* pFilePath, char* const argv[] )
{
    int signum, status;
    sigset_t newBlockedSignals, oldBlockedSignals;
    
    /* Restore all signal handlers to the system defaults. */
    struct sigaction oldActions[_NSIG];
    for (signum = 0; signum < _NSIG; signum++)
    {
        struct sigaction action;
        action.sa_handler = SIG_DFL;
        sigemptyset( &action.sa_mask );
        action.sa_flags = 0;

        status = sigaction( signum, &action, &oldActions[signum] );
    }
    
    /* Unblock all signals.*/
    sigemptyset( &newBlockedSignals );
    sigprocmask( SIG_SETMASK, &newBlockedSignals, &oldBlockedSignals );
    
    /* Now that this processes signal handlers are in the desired state, launch
     * the new process which will inherit the signal states.  This call does not
     * return if it suceeds.
     */
    return execvp( pFilePath, argv );
}


/*
 *  safe_fork_and_exec
 *
 *  Execute the specified file, preserving the current process.
 *  (Currently unused)
 *
 *  Parameters:
 *    pFilePath   - string specifying the file to execute
 *    argv        - the argument vector passed to new process;
 *                  the first argument should be the command name.
 *
 *  Returns:
 *    Returns 0 to the parent process.
 *    Does not return to the child process unless an error occurs,
 *    in which case 255 is returned.
 */
static
int safe_fork_and_exec( const char* pFilePath, char* const argv[] )
{
    pid_t child = fork();
    if (child)
    {
        /* Here if parent. */
        return 0;
    }
    
    /* Here if child. */
    return safe_exec( pFilePath, argv );
}


/*
 *  main
 *
 *  Execute the specified file, with all signals unblocked.
 *  The command lien format is:
 *
 *    superexec file-path arg1 arg2 ... argN
 *
 *  Returns:
 *    The exit status of the executed program,
 *    255 if the program could not be launched, or if no program was specified.
 */
int main( int argc, char* argv[] )
{
	int err;
    if (argc > 1)
    {
        err = safe_exec( argv[1], &argv[1] );
        if (err)
        {
        	printf( "Error: unable to execute %s\n", argv[1] );
        	return err;
        }
    }
        
    printf( "Error: no program specified.\n" );
    return 255;
}



