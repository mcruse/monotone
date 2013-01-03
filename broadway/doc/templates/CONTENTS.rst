=============================================================================
Directory Contents: `...`_/doc_/templates_
=============================================================================

.. _templates: CONTENTS.html
.. _doc: ../CONTENTS.html
.. _`...`: ../../CONTENTS.html

.. comment If you're creating a new CONTENTS file, don't blame me,
	   change the :Author: and :Contact: bibliographic fields.

:Author: Mark M. Evans
:Contact: mevans@envenergy.com
:Revision: $Revision: 20101 $
:Date: $Date: 2011-03-06 08:02:15 -0800 (Sun, 06 Mar 2011) $
:Copyright: 2003 Envenergy, Inc. Proprietary Information
:Abstract: Summary information about each source file in this directory.

.. contents::

Purpose
-------

This directory contains assorted template files that can be copied and
used as the starting point for that type of file.

Files
-----

CONTENTS.rst [#RST]_
    Summary information about each source file in this directory.

    Funnily enough, this file is also useful as a template for
    creating other CONTENTS.rst files.  For more detailed information
    on using this file as a template, see
    `Using The Contents File as a Template`_.

.. _`Using The Contents File as a Template`: CONTENTS_as_template.html

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

(none)

------------------------

.. [#RST] This source for this document, written using the
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
