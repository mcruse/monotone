/*
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
 *   This program displays the status of the mediator via its LED.  It also functions
 *   as a watchdog, in that once set to the running state the program expects to get
 *   periodic messages indicating that the mediator is "alive."  The PANIC state is
 *   entered if no messages are seen for at least two minutes.  Messages are sent to
 *   the program via a well-known named pipe.
 */
#include <stdio.h>
#include <assert.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#include <sys/types.h>
#include <signal.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>      // For errno and sys_errlst
#include <unistd.h>     // For read()
#include <stdlib.h>     // For exit()
#include <getopt.h>

typedef int bool;

#ifndef true
#define true 1
#endif

#ifndef false
#define false 0
#endif

static bool g_isDebug = false;

// Name of the proc file where LED patterns are written.
static const char* g_pPatternFileName = "/proc/mediator/pattern";

// Named pipe over which messages are received.
static const char* pPipeName = "/tmp/.blinky_bill.fifo";

static const char* pMorseDot       = "111";
static const char* pMorseSeparator = "000";
static const char* pMorseDash      = "111111111";   // Dot * 3
static const char* pMorseInterChar = "000000000";
static const char* pMorseBreak     = "000000000000000000000";  // Seperator * 7

static char* pPatternIdle = NULL;
static char* pPatternInstalling = NULL;
static char* pPatternRunning = NULL;
static char* pPatternError = NULL;
static char* pPatternPanic = NULL;

#define WATCHDOG_TIME_SECONDS 120
#define PATTERN_MAX_LEN 128


enum States
{
    NULL_STATE = 0,
    IDLE = '.',
    INSTALLING = 'I',
    RUNNING = 'R',
    ERROR = 'E',
    PANIC = 'P'
};

struct MorseCode
{
    char  ch;
    const char* pCode;
};

static const struct MorseCode codeTable[] =
{
    { 'A',  ".-"      },
    { 'B',  "-..."    },
    { 'C',  "-.-."    },
    { 'D',  "-.."     },
    { 'E',  "."       },
    { 'F',  "..-."    },
    { 'G',  "--."     },
    { 'H',  "...."    },
    { 'I',  ".."      },
    { 'J',  ".---"    },
    { 'K',  "-.-"     },
    { 'L',  ".-.."    },
    { 'M',  "--"      },
    { 'N',  "-."      },
    { 'O',  "---"     },
    { 'P',  ".--."    },
    { 'Q',  "--.-"    },
    { 'R',  ".-."     },
    { 'S',  "..."     },
    { 'T',  "-"       },
    { 'U',  "..-"     },
    { 'V',  "...-"    },
    { 'W',  ".--"     },
    { 'X',  "-..-"    },
    { 'Y',  "-.--"    },
    { 'Z',  "--.."    },
    { '1',  ".----"   },
    { '2',  "..---"   },
    { '3',  "...--"   },
    { '4',  "....-"   },
    { '5',  "....."   },
    { '6',  "-...."   },
    { '7',  "--..."   },
    { '8',  "---.."   },
    { '9',  "----."   },
    { '0',  "-----"   },
    { '.',  ".-.-.-"  },
    { ',',  "--..--"  },
    { '/',  "-..-."   },  
    { '+',  ".-.-."   },
    { '=',  "-...-"   },
    { '?',  "..--.."  },
    { '(',  "-.--."   },
    { ')',  "-.--.-"  },
    { '-',  "-....-"  },
    { '"',  ".-..-."  },
    { '_',  "..--.-"  },
    { '\'', ".----."  },
    { ':',  "---..."  },
    { ';',  "-.-.-."  },
    { '$',  "...-..-" }
};

#define codeTableSize sizeof( codeTable ) / sizeof( struct MorseCode )
#define CODE_CACHE_SIZE 2    // Power of 2


int SendPattern( const char* pPattern )
{
    FILE* pFile;
    
    assert( pPattern != NULL );
    assert( strlen( pPattern ) <= PATTERN_MAX_LEN );
    
    if (pFile = fopen( g_pPatternFileName, "w" ))
    {
        if (g_isDebug)
            printf( "sending:<%s>\n", pPattern );
        fputs( pPattern, pFile );
        fclose( pFile );
        return 0;
    }
    
    return errno;
}


char* MorseToPattern( const char* pText )
{
    char ch;
    int  i;
    char workBuffer[512];   // Build pattern on the stack.
    char* pPattern;
    
    workBuffer[0] = '\0';
    
    while (ch = toupper( *pText++ ))
    {
        if (isspace( ch ))
        {
            // Inter-word break..
            strcat( workBuffer, pMorseBreak );
        }
        else
        {
            const char* pCode = NULL;
            
            // Linear search of code table.
            if (!pCode)
            {
                for(i = 0; i < codeTableSize; i++)
                {
                    if (ch == codeTable[i].ch)
                    {
                        pCode = codeTable[i].pCode;
                        break;
                    }
                }
            }
            
            if (pCode)
            {
                char key;
                
                while (key = *pCode++)
                {
                    if (key == '.')
                    {
                        strcat( workBuffer, pMorseDot );
                    }
                    else if (key == '-')
                    {
                        strcat( workBuffer, pMorseDash );
                    }
                    
                    // Pause one count for key seperation if more to come.
                    if (*pCode)
                    {
                        strcat( workBuffer, pMorseSeparator );
                    }
                }
                
                // Inter-character pause, if more to come.
                if (*pText)
                {
                    strcat( workBuffer, pMorseInterChar );
                }
            }
        }
    }

    // End of text. Add inter-word break.
    strcat( workBuffer, pMorseBreak );
    
    pPattern = malloc( strlen( workBuffer ) + 1 );
    strcpy( pPattern, workBuffer );
    return pPattern;
}


//-----------------------------------------------//

void sigterm_handler( int signum )
{
    assert( signum == SIGTERM );
    SendPattern( "0" );
    exit( 0 );
}
    
    
//-----------------------------------------------//

void savePattern( char** pPatternPtr, const char* pNewPattern )
{
    if (*pPatternPtr)
        free( *pPatternPtr );
    *pPatternPtr = malloc( strlen( pNewPattern ) + 1 );
    strcpy( *pPatternPtr, pNewPattern );
}

bool isEmptyLine( const char* pLine )
{
    while (*pLine)
    {
        if (!isspace( *pLine ))
            return false;
        pLine++;
    }
    return true;
}

bool isValidPattern( const char* pPattern, int* iFirstBadChar )
{
    int i = 0;
    char ch;
    
    while (ch = pPattern[i])
    {
        if (ch == '\n')
            break;
            
        if (ch != '0' && ch != '1')
        {
            *iFirstBadChar = i;
            return false;
        }
        
        i++;
    }
    
    *iFirstBadChar = i;
    return i > 0;  
}

bool initializePatterns( const char* pConfigFileName )
{
    // Get patterns from the config file if one was specifed.
    if (pConfigFileName)
    {
        int col, line;
        char buffer[256];

        FILE* pCfg = fopen( pConfigFileName, "r" );
        if (!pCfg)
            return false;
 
        // Format for each line of the file is:
        // <ch>:<pattern>
        // where ch matches one of the state designators: .|I|R|E|P
        // and <pattern> is a string of 1's and 0's.
        line = 0;
        while (fgets( buffer, sizeof(buffer), pCfg ))
        {
            line++;
            if (buffer[0] == '#' || isEmptyLine( buffer ))
                continue;
            if (buffer[1] != ':')
            {
                printf( "%s:%d: expected ':' in column 2\n", pConfigFileName, line );
                continue;
            }
            if (!isValidPattern( &buffer[2], &col ))
            {
                printf( "%s:%d: bad format for pattern;\n  found '%c' in column %d, expected '0' or '1'\n",
                        pConfigFileName, line, buffer[col + 2], col + 3 );
                continue;
            }
            if (buffer[col + 2] == '\n')
            {
                buffer[col + 2] = '\0';
            }
            
            switch (buffer[0])
            {
            case IDLE:
                savePattern( &pPatternIdle, &buffer[2] );
                break;
                  
            case INSTALLING:
                savePattern( &pPatternInstalling, &buffer[2] );
                break;
                    
            case RUNNING:
                savePattern( &pPatternRunning, &buffer[2] );
                break;
                    
            case ERROR:
                savePattern( &pPatternError, &buffer[2] );
                break;
                    
            case PANIC:
                savePattern( &pPatternPanic, &buffer[2] );
                break;
                    
            default:
                printf( "%s:%d: unknown state;\n  found '%c' in column 1, expected one of <.IREP>\n",
                        pConfigFileName, line, buffer[0] );
                break;
            }
        }
        
        fclose( pCfg );
    }
    
    // Defaults
    if (!pPatternIdle)
        pPatternIdle = MorseToPattern( "T" );
    if (!pPatternInstalling)
        pPatternInstalling = MorseToPattern( "I" );
    if (!pPatternRunning)
        pPatternRunning = MorseToPattern( "O" );
    if (!pPatternError)
        pPatternError = MorseToPattern( "H" );
    if (!pPatternPanic)
        pPatternPanic = MorseToPattern( "SOS" );
    
    if (g_isDebug)
    {
        printf( "idle pattern is '%s'\n", pPatternIdle );
        printf( "installing pattern is '%s'\n", pPatternInstalling );
        printf( "running pattern is '%s'\n", pPatternRunning );
        printf( "error pattern is '%s'\n", pPatternError );
        printf( "panic pattern is '%s'\n", pPatternPanic );
    }
    
    return true;
}


//-----------------------------------------------//

// Provide some minimal help with the command-line options.
void displayHelp( const char* pProgName, const struct option* pOptions )
{
    printf( "usage: %s <options>\nvalid options are:\n", pProgName );
    while( pOptions->name )
    {
        printf( "  --%s", pOptions->name );
        if (pOptions->val)
            printf( " or -%c", pOptions->val );
        if (pOptions->has_arg)
            printf( " <arg>" );
        putchar( '\n' );
        
        pOptions++;
    }
}


int main( int argc, char* argv[] )
{
    struct sigaction act;
    int pipe;
    sigset_t sa_mask;
    int i, status;
    char buffer[256];
    ssize_t bytes_read;
    fd_set read_fds;
    struct timeval timer;
    enum States state = IDLE;
    enum States prev_state = NULL_STATE;
    char* pConfigFileName = NULL;
    extern int optind;
    extern char* optarg;
    int t_pipebroken = 0;

    //
    // Process command-line options.
    //

    while (true)
    {
        int opt;
        int option_index = 0;
        static struct option long_options[] =
        {
            { "debug",  0, 0, 'd' },
            { "config", 1, 0, 'c' },
            { "help",   0, 0, 'h' },
            { NULL,     0, 0, 0   }
        };

        opt = getopt_long( argc, argv, "c:dh", long_options, &option_index );
        if (opt == -1)
            break;

        switch (opt)
        {
        case 'c':
            pConfigFileName = optarg;
            break;

        case 'd':
            g_isDebug = true;
            break;

        case 'h':
            displayHelp( argv[0], long_options );
            return 0;

        case '?':      // Unknown or ambiguous option; error message displayed by getopt.
            printf( "use -h for help\n" );
            return 1;

        default:       // Huh?
            printf( "getopt error!\n" );
            return 1;
        }
    }

    while (optind < argc)
    {
        printf( "ignoring extraneous argument '%s'\n", argv[optind++] );
    }

    // Check for access to LED.
    if (access( g_pPatternFileName, W_OK ))
    {
        printf( "unable to access LED. '%s' is not writable\n", g_pPatternFileName );
        return 1;
    }
    
    // Initialize patterns.
    if (!initializePatterns( pConfigFileName ))
    {
        printf( "unabable to access %s\n", pConfigFileName );
        return 3;
    }

    //
    // Set up the SIGTERM signal handler.
    //
    
    sigemptyset( &sa_mask );
    
    act.sa_handler = sigterm_handler;
    act.sa_mask = sa_mask;
    act.sa_flags = 0;
    act.sa_restorer = NULL;

    status = sigaction( SIGTERM, &act, NULL );
    assert( status == 0 );
    
    //
    // Open the communications pipe over which commands are accepted.
    //
    if (access( pPipeName, F_OK ) != 0)
    {
        status = mkfifo( pPipeName, S_IRWXU );
        assert( status == 0 );
    }
    
    pipe = open( pPipeName, O_RDONLY|O_NONBLOCK );
    if (pipe < 0)
    {
        perror( "pipe open failed: " );
        return errno;
    }
    
    //
    // Main processing loop.
    //
    
    while (true)
    {
        if (state != prev_state)
        {
            switch (state)
            {
            case IDLE:                      // Initial state; app not running.
                // slow blink
                SendPattern( pPatternIdle );
                break;
                
            case INSTALLING:                // App is installing.
                SendPattern( pPatternInstalling );
                break;
                
            case RUNNING:                   // App is running, and being monitored.
                SendPattern( pPatternRunning );
                break;
                
            case ERROR:                     // App is running with errors, and being monitored.
                SendPattern( pPatternError );
                break;
                
            case PANIC:                     // App is dead or in BIG trouble.
                SendPattern( pPatternPanic );
                break;
                
            default:
                SendPattern( "10" );        // Huh? Unknown state! Blink like hell!
                break;
            }

            prev_state = state;
        }

        // Prepare file descriptor set and timer for select().
        FD_ZERO( &read_fds );
        FD_SET( pipe, &read_fds );
        timer.tv_sec = WATCHDOG_TIME_SECONDS;
        timer.tv_usec = 0;
        
        status = select( pipe + 1, &read_fds, NULL, NULL, &timer );
        
        // PANIC if watchdog timed out.
        if (status == 0)
        {
            if (g_isDebug)
                printf( "read time out.\n" );
            
            buffer[0] = PANIC;
            bytes_read = 1;
        }
        else
        {        
            bytes_read = read( pipe, (void*)&buffer, sizeof(buffer[0]) );
            if (bytes_read < 0)
            {
                perror( "pipe read failed" );
                return errno;
            }      
        }
        
        if (bytes_read > 0)
        {
            t_pipebroken = 0;
            state = (enum States)buffer[bytes_read - 1];
            if (g_isDebug)
                printf( "read %d byte(s): %c\n", bytes_read, state );
        }
        else
        {
            if (g_isDebug)
                printf( "read 0 bytes; pipe broken for %d seconds.\n", t_pipebroken );
                
            // Sleep for a while to prevent spinning wheels reading 0 bytes.
            timer.tv_sec = 5;
            timer.tv_usec = 0;
            status = select( 0, NULL, NULL, NULL, &timer );

            t_pipebroken += 5;
            if (t_pipebroken > WATCHDOG_TIME_SECONDS)
                state = PANIC;  // Pipe boken too long. Assume framework is no longer running.
          }
    }
 
    return 0;
}
