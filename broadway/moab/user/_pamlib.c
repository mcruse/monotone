/*
Copyright (C) 2010 2011 Cisco Systems

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
#include <security/pam_appl.h>
#include <security/pam_misc.h>

int conversation(int, const struct pam_message **, 
                 struct pam_response **, void *);
int validate(char *, char *);
const char * _pam_error(int errcode);

int conversation(int msg_count, 
                 const struct pam_message **msg, 
                 struct pam_response **resp, 
                 void *pw)
{
    struct pam_response *r = NULL;
    int i = 0;
    
    if (msg_count <= 0 || msg_count > PAM_MAX_NUM_MSG) 
        return PAM_CONV_ERR;

    if ((r = (struct pam_response *) calloc(msg_count, 
              sizeof(struct pam_response))) == NULL)
        return PAM_BUF_ERR;
    
    for(i=0; i<msg_count; ++i) {
        r[i].resp_retcode = 0;
        r[i].resp = strdup(pw);
    }

    *resp = r;
    return PAM_SUCCESS;
}

int validate(char *un, char *pw)
{
    int retval;
    pam_handle_t *pamh = NULL;
    char *app_name = "mpxauth";
    struct pam_conv conv = {conversation, pw};

    if (!un || !pw)
        return PAM_AUTH_ERR;
    
    retval = pam_start(app_name, un, &conv, &pamh);
    if (retval != PAM_SUCCESS) return retval;

    retval = pam_authenticate(pamh, 0);
    if (retval != PAM_SUCCESS) return retval;

    retval = pam_end(pamh, retval);
    if (retval != PAM_SUCCESS) return retval;

    return retval;
}

const char * _pam_error(int errcode)
{
    return pam_strerror(NULL, errcode);
}

int main(int agrc, char *argv[])
{
    /* I've got nothing to do!! */
    return 0;
}

