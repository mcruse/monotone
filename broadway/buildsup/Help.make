#=---------------------------------------------------------------------------
# emacs: this is a -*-Makefile-*-
# vim: ts=8 noexpandtab syntax=make
#
# Keep the help text for the build help system here.  This prevents the
# top-level makefile from getting bloated with help text.  This also means
# we can edit and test help text formatting without having to a frikkin'
# 'make reconfig' at every edit -n- save.
#=---------------------------------------------------------------------------

#   *-=-*-=-*-=-* SCOTT'S HELP TEXT FORMATTING GUIDELINES *-=-*-=-*-=-*-=-*
# 
# Generally, I choose to provide an easily parseable format that any true
# Unix geek understands -- the man page.  This, IM[not so]HO is probably
# the best way to provde detailed help on a subject in an easily digestible
# format.  Much better than that emacs-based 'info' crap.
#
# The only oddity here I know of is that rather than ending a line of text
# with a newline (\n), you must *start* each line of help text with a
# newline.  For some reason if you don't do this you get an extra space
# at the start of each line which can play hell when you're trying to make
# your carefully crafted help text look purty.  I'll look into this when I
# have more time.
#
#   *-=-*-=-*-=-* SCOTT'S HELP TEXT FORMATTING GUIDELINES *-=-*-=-*-=-*-=-*


#=---------------------------------------------------------------------------
# Name the <target>-help targets for the .PHONY declaration in the top
# Makefile.  This may not be the best pace to store this information but
# I'm trying to keep as much of the "help system" out of the makefile
# as possible.  Please keep these in alphabetical order, it really helps.

HELP_TARGETS=	all-help \
		autoconf-help \
		build-help \
		checkcvs-help \
		checksvn-help \
		clean-help \
		distclean-help \
		doc-help \
		flash-help \
		help \
		help-help \
		makecheck-help \
		montydoc-help \
		publish-help \
		reconfig-help \
		release-help \
		tagandchangelog-help


#=---------------------------------------------------------------------------
# Help text spitter-outter.

SHOWHELP=echo -e


#=---------------------------------------------------------------------------
# Generic message, duh.

COMING_SOON="\n*-=-* Under construction *-=-*\n"


#=---------------------------------------------------------------------------
# Pointer back to the build HOWTO.  Include this at the end of each help
# text section.

DISCLAIMER=\
"\nNOTE: The information provided here is intendended to be used for process" \
"\n      summarization.  The build HOWTO should always be considered the" \
"\n      authoritative document."


#=---------------------------------------------------------------------------
# Implementation of the help system.
#
# Please keep these in alphabetical order, it really helps.
#=---------------------------------------------------------------------------

#=---------------------------------------------------------------------------
# 'make all-help'

ALL_HELP=\
"ALL\n\nInvocation:\n 'make' (or 'make all')" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:\n  Build all known targets." \
"\n\nRemarks:" \
"\n  - This is GNU make's default target if one just types 'make' on the" \
"\n    command line." \
"\n  - This target behaves differently depending on where one is located in" \
"\n    the build tree.  If one is in..." \
"\n     ... the top-level directory then the entire tree is built." \
"\n     ... a child directory then just the child directory is built, even if" \
"\n         the child has sibling directories of its own." \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make autoconf-help'

AUTOCONF_HELP=\
"AUTOCONF\n\nInvocation:\n 'make autoconf'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:\n  Regenerate the configure script from the configure.in" \
"\n  source file and then re-execute the new configure script using the same" \
"\n  configure options.  Same as running setup_configure_script.sh from the" \
"\n  BROADWAY source directory."\
"\n\nRelated topics:" \
"\n  reconfig"\
"\n"\
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make build-help'

BUILD_HELP=\
"BUILD\n\nInvocation:\n  'make build'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:" \
"\n  The same as executing \"make reconfig; make; make tarball\" on the CLI." \
"\n\nRelated topics:" \
"\n  all, reconfig, tarball" \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make checkcvs-help'

CHECKCVS_HELP=\
"CHECKCVS\n\nInvocation:\n  'make checkcvs'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:" \
"\n  Verifies that your source tree is up to date and complains if it isn't." \
"\n\nRemarks:" \
"\n  - This is intended as a support rule for 'release' but might be of interest." \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make checksvn-help'

CHECKCVS_HELP=\
"CHECKSVN\n\nInvocation:\n  'make checksvn'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:" \
"\n  Verifies that your source tree is up to date and complains if it isn't." \
"\n\nRemarks:" \
"\n  - This is intended as a support rule for 'release' but might be of interest." \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make clean-help'

CLEAN_HELP=\
"CLEAN\n\nInvocation:\n  'make clean'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:\n  Clean a directory or tree.  \"Cleaning\" a tree is the act of" \
"\n  removing files that were generated as part of a build where make was the" \
"\n  vehicle in generating these files and directories." \
"\n\nRemarks:" \
"\n  - This target behaves differently depending on where one is located in" \
"\n    the build tree.  If one is in..." \
"\n     ... the top-level directory then the entire tree is cleaned." \
"\n     ... a child directory then just the child directory is cleaned, even if" \
"\n         the child has sibling directories of it's own." \
"\n\nRelated topics:" \
"\n  distclean" \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make distclean-help'

DISTCLEAN_HELP=\
"DISTCLEAN\n\nInvocation:\n  'make distclean'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:\n  Dist-clean a directory or tree.  \"Dist-cleaning\" a tree is the act of" \
"\n  removing files that were generated as part of a build where make was the" \
"\n  vehicle in generating these files and directories." \
"\n\nRemarks:" \
"\n  - This target behaves differently depending on where one is located in" \
"\n    the build tree.  If one is in..." \
"\n     ... the top-level directory then the entire tree is cleaned." \
"\n     ... a child directory then just the child directory is cleaned, even if" \
"\n         the child has sibling directories of it's own." \
"\n  - The distclean target is intended only for use in the top-level build" \
"\n    directory.  If one accidentally \"distclean\"s in a child directory" \
"\n    then it will be necessary to re-execute the configure script before" \
"\n    being able to build again." \
"\n\nRelated topics:" \
"\n  clean, reconfig" \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make doc-help'

DOC_HELP=\
"DOC\n\nInvocation:\n 'make doc'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:" \
"\n  Generate the documentation contained in supplemental files through out" \
"\n  the source repository." \
"\n\nRemarks:" \
"\n  - Requires montydoc." \
"\n  - Requires python's docutils." \
"\n\nRelated topics:" \
"\n  montydoc" \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make flash-help'

FLASH_HELP=\
"FLASH\n\nInvocation:\n  'make flash'" \
"\n\nAdditional parameters:" \
"\n  FLASH_MOE: Specify which MOE to use" \
"\n  FLASH_PKG: Specify which package from the broadway to use, default is" \
"\n             envenergy.mpx" \
"\n  FLASH_MNT: Where to mount the flash for burning, default is" \
"\n             [BUILD_DIR]/flash.d" \
"\n  FLASH_DEV: Specify your CF burner, default is /dev/sda" \
"\n  FLASH_TARBALL: Which 'prelease' tarball to use" \
"\n\nPurpose:" \
"\n  Burn a flash for a mediator." \
"\n\nRemarks:" \
"\n  - If you are not Mark or Scott, don't use this yet...\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make help'

#--------1---------2---------3---------4---------5---------6---------7-------8-|
HELP=\
"Valid make targets are:"\
"\n  all: build everything."\
"\n  autoconf: re-generate the configure script from source (configure.in) and"\
"\n      then reconfigure your build directory's build infrastructure."\
"\n  build: cut a developer's build."\
"\n  checkcvs: make sure your source tree is up-to-date."\
"\n  checksvn: make sure your source tree is up-to-date."\
"\n  clean: remove compiler generated files, do not touch build infrastructure."\
"\n  distclean: \"clean\"+delete build infrastructure files."\
"\n  doc: build documentation."\
"\n  flash: burn a flash for a Mediator."\
"\n  help: your're lookin' at it."\
"\n  makecheck: verify that build infrastructure files are up to date."\
"\n  montydoc: generate Montydoc documentation from source code."\
"\n  publish: 'scp' a competed developer or release tarball to labman."\
"\n  reconfig: re-execute the configure script with the same arguments that"\
"\n      were originally specified for a particular build directory."\
"\n  tagandchangelog: tag the source tree with the current version specified"\
"\n      in the BROADWAY file and generate a changelog."\
"\n  tarball: make a \"prelease\" tarball."\
"\n"\
"\nAdditionally, you can get detailed help for a particular target by" \
"\ninvoking 'make <target>-help.\n" \
$(DISCLAIMER)
#--------1---------2---------3---------4---------5---------6---------7-------8-|


#=---------------------------------------------------------------------------
# 'make help-help'

HELP_HELP="\nComedian. :-)\n"


#=---------------------------------------------------------------------------
# 'make makecheck-help'

MAKECHECK_HELP=\
"MAKECHECK\n\nInvocation:\n  'make makecheck'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:" \
"\n  Iterate over key build infrastructure files (configure script, makefiles" \
"\n  et cetera) to insure that they are up to date with their counterparts in" \
"\n  the source directory." \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make montydoc-help'

MONTYDOC_HELP=\
"MONTYDOC\n\nInvocation:\n  'make montydoc'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:" \
"\n  Generate the MontyDoc's derived from the source code.  This target" \
"\n  is only valid in top build directory since MontyDoc's are generated" \
"\n  against the entire source repository at this time." \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make publish-help'

PUBLISH_HELP=\
"PUBLISH\n\nInvocation:\n  'make publish'" \
"\n\nAdditional parameters:" \
"\n  PUB_USER: Specify an alternate username (default is 'mediator')." \
"\n  PUB_HOST: Specify an alternate hostname (default is 'mediator')." \
"\n  PUB_DIR:  Specify an alternate destination directory to scp the" \
"\n            tarball (default is '/home/mediator/dev')." \
"\n\nPurpose:" \
"\n  Publishes a finished tarball to labman." \
"\n\nRemarks:" \
"\n  - PUB_USER, PUB_HOST, and PUB_DIR are placeholders for now.  Will" \
"\n    implement when time permits." \
"\n\nRelated topics:" \
"\n  all, build, tarball, release" \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make reconfig-help'

RECONFIG_HELP=\
"RECONFIG\n\nInvocation:\n  'make reconfig'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:" \
"\n  Re-executes the configure script using the options originally specified" \
"\n  when configure was first invoked for a particular build tree." \
"\n\nRelated topics:" \
"\n  autoconf, distclean" \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make release-help'

RELEASE_HELP=\
"RELEASE\n\nInvocation:\n  'make release'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpse:" \
"\n  The same as executing:" \
"\n      make cvscheck; make autoconf; make tagandchangelog; make; make tarball" \
"\n  on the command line." \
"\n\nRelated topics:" \
"\n  autoconf, cvscheck, tagandchangelog, tarball" \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make tagandchangelog-help'

TAGANDCHANGELOG_HELP=\
"TAGANDCHANGELOG\n\nInvocation:\n  'make tagandchangelog'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:" \
"\n  Generate a changelog, tag the tree, and update the BROADWAY file." \
"\n\nRelated topics:" \
"\n  release" \
"\n" \
$(DISCLAIMER)


#=---------------------------------------------------------------------------
# 'make tarball-help'

TARBALL_HELP=\
"TARBALL\n\nInvocation:\n  'make tarball'" \
"\n\nAdditional parameters:\n  None." \
"\n\nPurpose:" \
"\n  Iterate over the build tree and assemble a finished broadway tarball." \
"\n" \
$(DISCLAIMER)


#=- EOF --------------------------------------------------------------------=#
