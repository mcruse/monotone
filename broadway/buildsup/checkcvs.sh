#!/bin/bash
#=--------------------------------------------------------------------------
# CHECKCVS.SH
#
# A quick-n-dirty shell script that invokes cvs to see whether or not
# the sources are up-to-date.  Intended for the 'make release' nonsense.
#=--------------------------------------------------------------------------


source_dir=`dirname $0 | sed -e 's~\/buildsup~~'`

pushd "${source_dir}" 1>/dev/null || {
    echo "ERROR: cannot get to the source directory."
    exit 1
}

cvs -n -q update 2>/dev/null | grep -q -c '^[MUP]' && {
    echo "CVS returned unexpected result."
    echo "Either there are modified or out of date files in the current source tree,"
    echo "or the \"cvs -n -q update\" command failed."

    exit 1
}

popd 1>/dev/null || {
    exit 1
}

exit 0

#=- EOF --------------------------------------------------------------------
