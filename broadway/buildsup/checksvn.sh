#!/bin/bash
#=--------------------------------------------------------------------------
# CHECKSVN.SH
#
# A quick-n-dirty shell script that invokes cvs to see whether or not
# the sources are up-to-date.  Intended for the 'make release' nonsense.
#=--------------------------------------------------------------------------


source_dir=`dirname $0 | sed -e 's~\/buildsup~~'`

pushd "${source_dir}" 1>/dev/null || {
    echo "ERROR: cannot get to the source directory."
    exit 1
}

svn status -u | egrep -v '^[XI ] [ L]  [KOTB ] ' | egrep -v '^Status against revision' | grep '.*'
if [ $? -eq 0 ]; then
    echo "*****************************************************************************"
    echo "*                                   ERROR                                   *"
    echo "* SVN returned unexpected result.                                           *"
    echo "* Either there are modified or out of date files in the current source tree *"
    echo "*****************************************************************************"
    exit 1
fi

popd 1>/dev/null || {
    exit 1
}

exit 0

#=- EOF --------------------------------------------------------------------
