##
# An odd sort of Makefile that generates the Makefile required to build the
# Python extension modules (shared libraries).  It ensures that the Makefile
# is generated from the source controlled input files (Makefile.pre.in and
# Setup.in, and not by modified target files (Makefile.pre, Makefile, and
# Setup).  It also checks the dependencies of the source files, which the
# standard Makefile doesn't seem to do.
#
# WARNING:  REQUIRES PYTHON=xxx argument.

all: boot.md5 valid

_MAKETARGETS=Makefile Makefile.pre Setup
_MAKESOURCES=Makefile.pre.in Setup.in
_MAKEFILES=$(_MAKETARGETS) $(_MAKESOURCES)

$(_MAKETARGETS):
	touch $(_MAKETARGETS)

boot.md5: $(_MAKEFILES)
	rm -f Makefile Makefile.pre Setup
	make -f Makefile.pre.in boot PYTHON=$(PYTHON)
	md5sum $(_MAKEFILES) >boot.md5

valid: eth.o ip.o npdu.o npdu_object.o \
	addr_object.o tag.o _bvlc.o

eth.o: eth.c lib.h eth.h
	rm -f eth.o

ip.o: ip.c lib.h ip.h _bvlc.h
	rm -f ip.o

npdu.o: npdu.c lib.h eth.h ip.h addr_object.h \
        npdu_object.h _bvlc.h
	rm -f npdu.o

npdu_object.o: npdu_object.c lib.h npdu_object.h
	rm -f npdu_object.o

addr_object.o: addr_object.c addr_object.h lib.h
	rm -f addr_object.o

tag.o: tag.c data.h _data.h lib.h
	rm -f tag.o

data.o: data.c _data.h lib.h
	rm -f data.o

_bvlc.o: _bvlc.c _bvlc.h lib.h
	rm -f _bvlc.o
