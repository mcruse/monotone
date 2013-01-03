#!/bin/bash

abspath () {
    local old_dir
    old_dir=$(pwd)
    cd $1
    result=$(pwd)
    cd $old_dir
    echo $result
}

make_stylesheet () {
    local path
    local file
    local stylesheet
    local old_dir
    stylesheet=$(expr "x$1" : 'x[^=]*=\(.*\)')
    test x"" == x$stylesheet && return 0
    test x\"\" == x$stylesheet && return 0
    test x\'\' == x$stylesheet && return 0
    old_dir=$(pwd)
    dir=$(dirname $stylesheet)
    file=$(basename $stylesheet)
    cd $dir || exit 1
    make -s $file || exit 1
    cd $old_dir || exit 1
}

RST2LATEX_STYLESHEET=--stylesheet=""
RST2LATEX_ARGS=""
CLEANUP=1
IN_FILE="--in-file=filename"
OUT_FILE="--out-file=filename"

for option
do
    case $option in
    --stylesheet=*) RST2LATEX_STYLESHEET=$option ;;
    --in-file=*) arg=$(expr "x$option" : 'x[^=]*=\(.*\)')
		 IN_FILE=$(abspath $(dirname "$arg"))/$(basename "$arg")
		 ;;
    --out-file=*) arg=$(expr "x$option" : 'x[^=]*=\(.*\)')
		  OUT_FILE=$(abspath $(dirname "$arg"))/$(basename "$arg")
		  ;;
    --no-clean-up) CLEANUP=0 ;;
    --clean-up) CLEANUP=1 ;;
    --*) RST2LATEX_ARGS="${RST2LATEX_ARGS} $option" ;;
    -*) echo "Old-style arguments are not acceopted." >&2
	exit 1
	;;
    *) echo "$(basename $0): There are no positional arguments ($option)." >&2
       exit 1
       ;;
    esac
done

make_stylesheet "${RST2LATEX_STYLESHEET}" || exit 1

RST2LATEX_ARGS="${RST2LATEX_ARGS} ${RST2LATEX_STYLESHEET}"

BUILDSUP_DIR=$(abspath $(dirname $0))
SITE_PACKAGES_DIR=${BUILDSUP_DIR}/site-packages
DOCUTILS_DIR=${SITE_PACKAGES_DIR}/docutils
DOCUTILS_TOOLS_DIR=${DOCUTILS_DIR}/tools
BROADWAY_DIR=${BUILDSUP_DIR}/..

export PYTHONPATH=${SITE_PACKAGES_DIR}
python2.2 ${DOCUTILS_TOOLS_DIR}/rst2latex.py ${RST2LATEX_ARGS} \
	${IN_FILE} > ${OUT_FILE}
result=$?
rootname=$(echo "$IN_FILE" | sed 's/^\(.*\)\.[^.]\+$/\1/g')
test $CLEANUP -ne 0 && rm -f $rootname.aux
test $CLEANUP -ne 0 && rm -f $rootname.log
test $CLEANUP -ne 0 && rm -f $rootname.out
test $CLEANUP -ne 0 && rm -f $rootname.toc
exit $result
