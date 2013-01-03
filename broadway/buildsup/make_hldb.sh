#!/bin/bash

COMMAND=`basename $0`

if test "$1" == "--help"; then
    echo "$COMMAND: Create a local reStructuredText Hyperlink Database."
    echo ""
    echo "USAGE: $COMMAND input-file output-file"
    echo ""
    echo "    input-file   The source file."
    echo "    output-file  The generated file with all \$\(proot\) references"
    echo "                 'normalized' to the local directory."
    echo ""
    exit 0
fi

if test "$#" -ne 2; then
    echo "$COMMAND: requires exaclty two arguments."
    echo "  '$COMMAND --help' for more information."
    exit 1
fi

source="$1"
target="$2"

test -f "$1"
if test $? -ne 0; then
    echo "$COMMAND: \'$1\' does not exist."
    exit 1
fi

echo ".. Generated with $0 \"$@\"\n" |
    cat "$1" |
    sed "{
s#\\\$(proot)#file://$(proot)#g
s#\\\$(psource)#file://$(psource)#g
}" > "$2"
