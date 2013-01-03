# vim: ts=8 noexpandtab syntax=make
#
# Make commands for RPM-y things.  All commands that operate on RPMs that
# have legacy counterparts are prefixed with 'rpm_'; e.g.: rpm_clean.
#=---------------------------------------------------------------------------=#

#=---------------------------------------------------------------------------=#
# Directories, key files, &c...

RPM_TOP		:= $(BUILD_DIR)/rpm.d
RPM_BUILD	:= $(RPM_TOP)/BUILD
RPM_SRCS	:= $(RPM_TOP)/SOURCES
RPM_RPMS	:= $(RPM_TOP)/RPMS/i386

FW_VERSION	:= $(shell cat $(top_srcdir)/BROADWAY | cut -f 1-3 -d .)
FW_RELEASE	:= $(shell cat $(top_srcdir)/BROADWAY | cut -f 4-5 -d .)

FW_BUILDSUP	:= $(top_srcdir)/buildsup
RPM_BUILDSUP	:= $(BUILD_DIR)/buildsup

# This file is "included" in the rpm SPEC files.
RPMSPEC_INC	:= $(RPM_BUILDSUP)/framework_rpmspec_inc
RPMSPEC_INC_SRC	:= $(FW_BUILDSUP)/framework_rpmspec_inc.in

FW_RPM_SPEC	:= $(RPM_BUILDSUP)/framework.spec
FW_RPM_SPEC_SRC	:= $(FW_BUILDSUP)/framework.spec.in
FW_RPM		:= $(RPM_RPMS)/framework-$(FW_VERSION)-$(FW_RELEASE).i386.rpm

MPX_RPM_SPEC	:= $(RPM_BUILDSUP)/mpx.spec
MPX_RPM_SPEC_SRC:= $(FW_BUILDSUP)/mpx.spec.in
MPX_RPM		:= $(RPM_RPMS)/mpx-$(FW_VERSION)-$(FW_RELEASE).i386.rpm

#=---------------------------------------------------------------------------=#
# Saves a lot of typing...

SPEC_FILES	:=	$(FW_RPM_SPEC) \
			$(MPX_RPM_SPEC)

SUPPORT_FILES	:=	$(RPM_SPEC_INC) \
			rpms

#=---------------------------------------------------------------------------=#

.PHONY: fw_rpm
fw_rpm: $(FW_RPM)
$(FW_RPM): rpm_init
	@rpmbuild --define "_topdir $(RPM_TOP)" -bb $(FW_RPM_SPEC)

.PHONY: mpx_rpm
mpx_rpm: $(MPX_RPM)
$(MPX_RPM): rpm_init
	@rpmbuild --define "_topdir $(RPM_TOP)" -bb $(MPX_RPM_SPEC)

#=---------------------------------------------------------------------------=#

.PHONY: rpm_clean
rpm_clean: clean
	rm -rf $(RPM_RPMS)/*$(FW_VERSION)-$(FW_RELEASE)*

#=---------------------------------------------------------------------------=#

.PHONY: rpm_distclean
#>>>rpm_distclean: distclean
rpm_distclean:
	rm -rf $(RPM_TOP) $(SPEC_FILES) $(SUPPORT_FILES) *.tgz

#=---------------------------------------------------------------------------=#

.PHONY: rpm_init
rpm_init:	$(RPM_BUILD) \
		$(RPM_SRCS)  \
		$(RPM_RPMS) \
		$(RPMSPEC_INC) \
		$(FW_RPM_SPEC) \
		$(MPX_RPM_SPEC) \
		rpms

#=---------------------------------------------------------------------------=#

.PHONY: rpm_variables
rpm_variables:
	@(echo -ne	"Variables for the RPM stuff:" \
			"\nSOURCE_DIR.................: $(top_srcdir)" \
			"\nBUILD_DIR..................: $(BUILD_DIR)" \
			"\nRPM_TOP....................: $(RPM_TOP)" \
			"\nRPM_BUILD..................: $(RPM_BUILD)" \
			"\nRPM_SRCS...................: $(RPM_SRCS)" \
			"\nRPM_RPMS...................: $(RPM_RPMS)" \
			"\nFW_BUILDSUP................: $(FW_BUILDSUP)" \
			"\nRPM_BUILDSUP...............: $(RPM_BUILDSUP)" \
			"\nRPMSPEC_INC................: $(RPMSPEC_INC)" \
			"\nRPMSPEC_INC_SRC............: $(RPMSPEC_INC_SRC)" \
			"\nFW_RPM_SPEC................: $(FW_RPM_SPEC)" \
			"\nFW_RPM_SPEC_SRC............: $(FW_RPM_SPEC_SRC)" \
			"\nMPX_RPM_SPEC...............: $(MPX_RPM_SPEC)" \
			"\nMPX_RPM_SPEC_SRC...........: $(MPX_RPM_SPEC_SRC)" \
			"\n"; \
	)

#=---------------------------------------------------------------------------=#
# Create stuff necessary to carry out a successful rpm build.  DO NOT flag
# these as .PHONY or they won't get created.

$(RPM_BUILD):
	@mkdir -m 0755 -p $@

$(RPM_SRCS):
	@mkdir -m 0755 -p $@

$(RPM_RPMS):
	@mkdir -m 0755 -p $@

$(FW_RPM_SPEC): $(FW_RPM_SPEC_SRC) Makefile
	@sed	-e 's#@PKG_NAME@#framework#g' \
		-e 's#@PKG_VERSION@#$(FW_VERSION)#g' \
		-e 's#@PKG_RELEASE@#$(FW_RELEASE)#g' \
		-e 's#@BUILD_RC@#$(BUILDTYPE)#g' \
	$< > $@

$(MPX_RPM_SPEC): $(MPX_RPM_SPEC_SRC) Makefile
	@sed	-e 's#@PKG_NAME@#mpx#g' \
		-e 's#@PKG_VERSION@#$(FW_VERSION)#g' \
		-e 's#@PKG_RELEASE@#$(FW_RELEASE)#g' \
		-e 's#@BUILD_RC@#$(BUILDTYPE)#g' \
	$< > $@

$(RPMSPEC_INC): $(RPMSPEC_INC_SRC)
	@sed	-e 's#@SOURCE@#$(RPMSPEC_INC_SRC)#g' \
		-e 's#@FW_BUILDROOT@#$(RPM_TOP)#g' \
		-e 's#@FW_VERSION@#$(FW_VERSION)#g' \
		-e 's#@FW_RPM_RELEASE@#$(FW_RELEASE)#g' \
		-e 's#@FW_PYTHON@#$(PYTHON)#g' \
		-e 's#@FW_PYGCC@#$(PYGCC)#g' \
		-e 's#@FW_SOURCEDIR@#$(top_srcdir)#g' \
		-e 's#@FW_BUILDDIR@#$(BUILD_DIR)#g' \
		-e 's#@BUILD_RC@#$(BUILDTYPE)#g' \
	$< > $@

rpms:
	@ln -s $(RPM_RPMS) $@

#=- EOF ---------------------------------------------------------------------=#
