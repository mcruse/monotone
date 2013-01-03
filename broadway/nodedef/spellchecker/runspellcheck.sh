#!/bin/bash
cat ./preamble.txt ./goodwords.txt ./questionablewords.txt > combowords.txt

cat ../master.script | aspell -l -p ./combowords.txt | sort | uniq
