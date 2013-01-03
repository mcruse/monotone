#!/usr/bin/env /bin/bash
#=----------------------------------------------------------------------------
# SETUP_CONFIGURE_SCRIPT.SH
#
# Purpose:
#     Run the necessary autoXXXX programs to get a 'configure' script
#     generated.
#
# Author:
#     S.T. Mansfield (smansfield@envenergy.com)
#
# Remarks:
#     Craig picked this name, not me. :-)
#=----------------------------------------------------------------------------

cd $(dirname $0)

adir=/opt/envenergy/devtools/3.0/bin/
if [ ! -d ${adir} ]
then
    echo "WARNING: using autoconf from PATH!"
    unset adir
fi

#
# Removed existing autoconf cache
rm -rf autom4te.cache

silent=0
[ "${1}" == "silent" ] && {
    silent=1
}

[ $silent == 0 ] && {
    echo "Preparing your source directory for 'configure':"
}

#
# ACLOCAL is used to generate interim support files and process any user-
# defined macros that configure(.in) needs.  It really only needs to be run
# if the configure.in script changes...
#
[ $silent == 0 ] && { echo -n "  Running aclocal..."; }
${adir}aclocal || exit 1
[ $silent == 0 ] && { echo "done."; }

#
# AUTOHEADER generates the 'config.h.in' header file for inclusion
# in your sources.
#
[ $silent == 0 ] && { echo -n "  Running autoheader..."; }
${adir}autoheader || exit 1
[ $silent == 0 ] && { echo "done."; }

#
# AUTOCONF generates configure from configure.in and any macros that aclocal
# spewed forth in the 'autom4te' directory...
#
[ $silent == 0 ] && { echo -n "  Running autoconf..."; }
${adir}autoconf || exit 1
[ $silent == 0 ] && { echo "done."; }

# Force use of /bin/bash:
sed s:'/bin/sh:/usr/bin/env bash:g' configure >configure.bash
chmod a+x configure.bash
mv -f configure.bash configure

[ $silent == 0 ] && {
    echo "Preparation complete, you may now run 'configure' from your build directory"
}

exit 0

#=----------------------------------------------------------------------------
# End.
#=----------------------------------------------------------------------------
