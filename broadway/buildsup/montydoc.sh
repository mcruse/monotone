#!/bin/bash

abspath () {
    local old_dir
    old_dir=$(pwd)
    cd $1
    result=$(pwd)
    cd $old_dir
    echo $result
}

BUILDSUP_DIR=$(abspath $(dirname $0))
MONTY_DOC_DIR=${BUILDSUP_DIR}/monty_doc
BROADWAY_DIR=${BUILDSUP_DIR}/..
cd ${BROADWAY_DIR}
python2.2 ${MONTY_DOC_DIR}/monty_doc.py -p mpx -t $1
