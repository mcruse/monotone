=====================================
Using The Contents File as a Template
=====================================

When copied as a template, update the path in the title to
reflect the path to the directory of the current
CONTENTS.rst file.  Each element in the path should be a
reStructuredText hyperlink reference.
::

 =============================================================================
 Directory Contents: `...`_/doc_/templates_                                   
 =============================================================================

There should be a reStructuredText hyperlink target for
each element in the title path (which are reStructuredText
hyperlink references).  These targets must use relative
paths.  It's easiest to update the relative paths by
starting with the current directory's CONTENTS.html file
and working backward to the build's root directory
(`...`).

::

 .. _templates: CONTENTS.html
 .. _doc: ../CONTENTS.html
 .. _`...`: ../../CONTENTS.html

If you're creating a new CONTENTS file, don't blame me,
change the :Author: and :Contact: bibliographic fields.

::

 :Author: Mark M. Evans
 :Contact: mevans@envenergy.com
 :Revision: $Revision: 20101 $
 :Date: $Date: 2011-03-06 08:02:15 -0800 (Sun, 06 Mar 2011) $
 :Copyright: 2003 Envenergy, Inc. Proprietary Information
 :Abstract: Summary information about each source file in this directory.

  .. contents::

  Purpose
  -------

The purpose should be brief, but describe the
organizational intent behind the directory.

::

 This directory contains assorted template files that can be copied and
 used as the starting point for that type of file.

 Files
 -----

List each source file and a brief description of the source
file using the markup for a definition list.  If there is
any supplemental documentation for a file or set of files,
then include appropriate links to the documentation.

::

 CONTENTS.rst [#RST]_
    Summary information about each source file in this directory.

    Funnily enough, this file is also useful as a template for
    creating other CONTENTS.rst files.  The source [#RST]_ to this
    file is chalk full of comments on using it as a template.

 Makefile.in
    The makefile used to generate this directory's formatted
    documentation.

 Makefile.in.template
    Template for creating a new Makefile that is compatible with the
    current build system.

    See `Makefile.rst`_ for more information.  The build
    process also generates this information in html__ and PDF__ formats. 

 .. _`Makefile.rst`: Makefile.rst
 .. __: Makefile.html
 .. __: Makefile.pdf

 Directories
 -----------

List each subdirectory with a brief description using the
markup for a definition list.  Each directory name should
be a reStructuredText hyperlink reference.  For each
reStructuredText hyperlink reference, create a
corresponding target that points to the directory's
generated CONTENTS.html file.  If there are directories,
remove the (none) statement.

::

 (none)

 ------------------------


 .. [#RST] The source for this document, written using the
           ReStructuredText markup language which is part of Python's
           docutils package.  Modifications to this document must
           conform to the `reStructuredText Markup Specification`_.  If
           this is your first exposure to reStructuredText, please read
           `A ReStructuredText Primer`_ and the
	   `Quick reStructuredText`_ user reference first.

 .. _`reStructuredText Markup Specification`:
    http://docutils.sourceforge.net/spec/rst/reStructuredText.html
 .. _`A ReStructuredText Primer`:
    http://docutils.sourceforge.net/docs/rst/quickstart.html
 .. _`Quick reStructuredText`:
    http://docutils.sourceforge.net/docs/rst/quickref.html
