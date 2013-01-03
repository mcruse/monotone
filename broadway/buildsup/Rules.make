#=---------------------------------------------------------------------------
# emacs: this is a -*-Makefile-*-
# vim: ts=8 noexpandtab syntax=make
#
# The purpose of this file is to eliminate much of the redundancy of work
# done in individual Makefiles by defining and implementing common tasks
# here instead of said Makefiles.
#=---------------------------------------------------------------------------


#=---------------------------------------------------------------------------
# Define targets that aren't files; speeds up the build a bit.

.PHONY:	do_makeall doc dummy target tools tests clean distclean \
	prelease prelease-d unittest

#=---------------------------------------------------------------------------
# Top-level directory of the build tree (the directory where you ran
# 'configure ...'  Used for prelease and prelease-d targets, and possibly
# others in the future.
#
# Do not set this here, the top-level Makefile sets this and passes it down.

# BUILD_TLD =


#=---------------------------------------------------------------------------
# Define zero or more flist(s) here, sans '.flist' extension.  For example:
#   PRELEASE = broadway \
#              broadway.core \
#              trane.demo
#
# Used by 'prelease' and 'prelease-d' rules (and possibly others).
#
# Do not set this here, set in each subsystem's 'Makefile.in'

# PRELEASE =

#=---------------------------------------------------------------------------
# Used for prelease and prelease-d targets.
#
# Do not set this here, it will be automagically figgered out each time
# this file is included.

PR_PATH = $(shell pwd | sed -e 's~$(BUILD_TLD)~~' | sed -e 's~^/~~')


#=---------------------------------------------------------------------------
# Support for alternate location for package building.
#
# Do not set this here, use "make DESTDIR='dir' <build|release>'

DESTDIR =


#=---------------------------------------------------------------------------
# How to compile C and C++ sources.

.SUFFIXES: .c .cc .cpp .o

%.o: $(srcdir)/%.c
	$(CC) $(CFLAGS) $(INCLUDES) -c -o $@ $<

%.o: $(srcdir)/%.cc
	$(CC) $(CLAGS) $(INCLUDES) -c -o $@ $<

%.o: $(srcdir)/%.cpp
	$(CXX) $(CFLAGS) $(INCLUDES) -c -o $@ $<

#=---------------------------------------------------------------------------
# How to "compile" python sources.

.SUFFIXES: .py .pyc .pyo

%.pyc: $(srcdir)/%.py
	$(PYGCC) $(PYGCCFLAGS) $<

%.pyo: $(srcdir)/%.py
	$(PYGCC) $(PYGCCFLAGS) $<

#=---------------------------------------------------------------------------
# How to "compile" image files.

.SUFFIXES: .bmp .gif .jpg .jpeg .JPG .ico .png 

%.bmp: $(srcdir)/%.bmp
	cp -fp $(srcdir)/$@ .

%.gif: $(srcdir)/%.gif
	cp -fp $(srcdir)/$@ .

%.jpg: $(srcdir)/%.jpg
	cp -fp $(srcdir)/$@ .

%.jpeg: $(srcdir)/%.jpeg
	cp -fp $(srcdir)/$@ .

%.JPG: $(srcdir)/%.JPG
	cp -fp $(srcdir)/$@ .

%.ico: $(srcdir)/%.ico
	cp -fp $(srcdir)/$@ .

%.png: $(srcdir)/%.png
	cp -fp $(srcdir)/$@ .

#=---------------------------------------------------------------------------
# How to "compile" web-related files.

.SUFFIXES: .CSS .css .htm .html .js .wjs .psp .jar

%.css: $(srcdir)/%.css
	cp -fp $(srcdir)/$@ .

%.CSS: $(srcdir)/%.CSS
	cp -fp $(srcdir)/$@ .

%.html: $(srcdir)/%.html
	cp -fp $(srcdir)/$@ .

%.htm: $(srcdir)/%.htm
	cp -fp $(srcdir)/$@ .

%.js: $(srcdir)/%.js
	cp -fp $(srcdir)/$@ .

%.wjs: $(srcdir)/%.wjs
	cp -fp $(srcdir)/$@ .

%.psp: $(srcdir)/%.psp
	cp -fp $(srcdir)/$@ .

%.jar: $(srcdir)/%.jar
	cp -fp $(srcdir)/$@ .


#=---------------------------------------------------------------------------
# How to "compile" data related files.

.SUFFIXES: .xml .md5 .dtd

%.xml: $(srcdir)/%.xml
	cp -fp $(srcdir)/$@ .

%.md5: $(srcdir)/%.md5
	cp -fp $(srcdir)/$@ .

%.dtd: $(srcdir)/%.dtd
	cp -fp $(srcdir)/$@ .

#=---------------------------------------------------------------------------
# How to generate documentation.

.SUFFIXES: .rst .html .latex .pdf .txt

%.rst:  $(srcdir)/%.rst
	cp -fp $(srcdir)/$@ .

# It's important that this rule rely on the build target copy of the
# %.rst file.
%.html: %.rst document.hldb
	$(RST2HTML) $(RST2HTML_ARGS) --in-file=$< --out-file=$@

# It's important that this rule rely on the build target copy of the
# %.rst file.
%.latex: %.rst document.hldb
	$(RST2LATEX) $(RST2LATEX_ARGS) --in-file=$< --out-file=$@

# It's important that this rule rely on the build target copy of the
# %.latex and %.rst file.
%.pdf: %.rst
	$(RST2PDF) $(RST2PDF_ARGS) --in-file=$< --out-file=$@

%.pdf:  $(srcdir)/%.pdf
	cp -fp $(srcdir)/$@ .

%.txt:  $(srcdir)/%.txt
	cp -fp $(srcdir)/$@ .

# Generate a local, directory 'normalized', document hyperlink database.
document.hldb: $(abs_top_srcdir)/doc/document.hldb.in
	$(abs_top_srcdir)/buildsup/make_hldb.sh $< $@

#=---------------------------------------------------------------------------
# Rule: all
#
#   Get the TARGETS built.  This is the default rule if one types in 'make'
#   at the command line.  Implement the 'do_makeall' rule in each Makefile.

all: do_makeall


#=---------------------------------------------------------------------------
# Rule: clean
#
#   Clean up all generated output.

clean:
	@for delFile in $(TARGETS) $(TOOLS) $(TESTS) $(DOC); do \
		if test -d $$delFile; then \
			rm -rf $$delFile; \
		else \
			rm -f $$delFile; \
		fi \
	done
	@rm -f *.o *.a *.so
	@rm -f document.hldb

#=---------------------------------------------------------------------------
# Rule: devlinks
#
#   Create symbolic links to source files.  <shudder>
#
# NOTE: Just a placeholder for now until I figure out a way to
#       transmogrify a target back to it's source (.pyc -> .py, .pyo -> .py,
#       .o -> .c, ad nauseum).  Prolly an uglee 'sed' script will do it.
#
#devlinks:
#	@for link_to in $(TARGETS); do \
#		ln -s $(srcdir)/$$link_to || exit 1; \
#	done


#=---------------------------------------------------------------------------
# Rule: distclean
#
#   Clean up all generated output, including output from 'configure.'

distclean: clean
	@rm -f Makefile


#=---------------------------------------------------------------------------
# Rule: tarball
#
#   For each subdirectory that produces output to the finished product,
#   via the TARGETS makefile target.

tarball:
ifeq ($(BUILD_TLD),)
	@echo This can only be done from the top-level build directory, outta here...
	exit 127
else

ifneq ($(PRELEASE),)
	# Copy all of the files built by this Makefile into its package(s)
	# release directories.  NOTE:  Tar is used to allow a Makefile to
	# package sub-directories that do not have RZ Makefiles of their own.
	# This is useful when including third party elements in our source
	# tree (like dojo and xtree) or large directory trees of files we just
	# want to copy over (like omega and wep-pages in general).
	for work_dir in $(PRELEASE); do \
		rdir="$(BUILD_TLD)/prelease.d/$$work_dir/broadway/$(PR_PATH)";\
		mkdir -p $${rdir} ; \
		[ "$(TARGETS)" != "" ] && \
			tar cf - $(TARGETS) | (cd $${rdir} && tar xpf -) || \
			true; \
	done
endif #ifneq PRELEASE
endif #ifeq BUILD_TLD


#=---------------------------------------------------------------------------
# Rule: unittest
#
#   Execute any unit tests.

unittest:
	@for file in $(TESTS); do \
		$(PYTHON) $$file; \
	done

#=---------------------------------------------------------------------------
# Rule: sm_pub
#
#   Helps me with moe 2.2+python 2.3 integration efforts *STM*

_moe_path := $(shell pwd | sed -e 's~/opt/build/broadway-dt4~/usr/lib/broadway~')
# MAGIC NUMBER ALERT! ...............^^^^^^^^^^^^^^^^^^^^^^^

sm_pub:
	@for file in $(TARGETS); do \
		scp $$file root@scottmoe:$(_moe_path)/.; \
	done

#=- EOF --------------------------------------------------------------------=#
