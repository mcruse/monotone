##
# An odd sort of Makefile that generates the Makefile required to build the
# Python extension modules (shared libraries).  It ensures that the Makefile
# is generated from the source controlled input files (Makefile.pre.in and
# Setup.in, and not by modified target files (Makefile.pre, Makefile, and
# Setup).  It also checks the dependencies of the source files, which the
# standard Makefile doesn't seem to do.
#

all: boot.md5 valid

_MAKETARGETS=Makefile Makefile.pre Setup
_MAKESOURCES=Makefile.pre.in Setup.in
_MAKEFILES=$(_MAKETARGETS) $(_MAKESOURCES)

$(_MAKETARGETS):
	touch $(_MAKETARGETS)

boot.md5: $(_MAKEFILES)
	rm -f Makefile Makefile.pre Setup
	make -f Makefile.pre.in boot
	md5sum $(_MAKEFILES) >boot.md5

valid: _eth.o

_eth.o: _eth.c
	rm -f _eth.o
