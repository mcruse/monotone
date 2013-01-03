===============================================================================
*re*\ Structured\ *Text* Tips and Tricks
===============================================================================

:Author: Mark M. Evans
:Contact: mevans@envenergy.com
:Revision: $Revision: 20101 $
:Date: $Date: 2011-03-06 08:02:15 -0800 (Sun, 06 Mar 2011) $
:Copyright: 2003 Envenergy, Inc. Proprietary Information
:Abstract: Tips, tricks and some other general information to using
           reStructuredText.

.. include:: document.hldb

.. contents::

Creating and Using Shared Document Hyperlinks
=============================================

One of the major problems with documentation is accurately maintaining
inter-document cross-references.  The ability to link together documents is
extremely powerful and can make the whole much greater then the some of the
parts by helping the user locate relavent information quickly.  Conversely,
when the links are not maintained, the documents appear out of date and fall
into disuse.

The Mediator Application Build system addresses the issue of maintaining
inter-document cross-references in reStructuredText by supporting the concept
of a shared Document HyperLink DataBase.  Basically, there is a common source
file |document_hldb_in| which has an entry for each shared documents.  This
source file maps a reStructuredText `Substitution References`_ to a
`Hyperlink Reference`_ and defines the coorosponding `Hyperlink Target`_.
Finally, The `Hyperlink Target`_\ 's link-block can contain expansion commands
[#]_ which are 'compiled' at build time into a relative path [#]_\ .

For every build directory where reStructuredText documents are used as source
files [#]_, the shared Document HyperLink DataBase is compiled into a
'normalized' Document HyperLink DataBase.

.. [#] Currently, '$(proot)' and '$(psource)' are the supported expansion
       commands.

.. [#] This conversion occurs via the make_hldb which.  ACTUALLY,
       make_hldb CREATES AN ABSOLUTE PATH, BUT THAT IS ONLY TEMPORARY.

.. [#] reStructuredText documents can currently be used to generate latex,
       html, and pdf files.

.. _`Substitution References`:
   http://docutils.sourceforge.net/spec/rst/reStructuredText.html#substitution-references

.. _`Hyperlink Reference`:
   http://docutils.sourceforge.net/spec/rst/reStructuredText.html#hyperlink-references

.. _`Hyperlink Target`:
   http://docutils.sourceforge.net/spec/rst/reStructuredText.html#hyperlink-targets

Referencing Maintainable Hyperlinks
-----------------------------------

In a document that you want to use a commonly defined reference link, simply
include the document.hldb file [#]_ anywhere in the source of your
document::

  .. include:: document.hldb

.. [#] The local document.hldb file is created as a standard part of the
       build process for any directory that generates output files from
       reStructuredTest input files.

Once document.hldb has been included, then any document defined in
|document_hldb_in| there can be referred to via its substitution reference::

  Here is a reference to the |NodeDef_Guidelines| ...

Which will be rendered as:

  Here is a reference to the |NodeDef_Guidelines| ...

Creating Maintainable Hyperlinks
--------------------------------

To add a new document to the Common HyperLink DataBase, define a document
substitution reference and a document target link in the |document_hldb_in|
file::

    .. |NodeDef_Guidelines| replace:: `NodeDef Guidelines`_
    .. _`NodeDef Guidelines`: $(proot)/nodedef/NodeDefGuidelines.html

For readability the document definitions should comply with the following
rules:

1. All statements for a single document should be grouped without whitespace.
2. The substitution reference should proceed the hyperlink target.
3. There should be a single blank line between document definitions.
4. Document definitions should be alphabatized by the substitution reference.
5. If the `Hyperlink Target`_ refers to a file contained in the build
   directories, then the path should be specified relative to $(proot).  If the
   `Hyperlink Target`_ refers to a file contained in the source directories
   [#]_, then the path should be specified relative to $(psource).

::

  .. |NodeDef_Guidelines| replace:: `NodeDef Guidelines`_
  .. _`NodeDef Guidelines`: $(proot)/nodedef/NodeDefGuidelines.html

  .. |document_hldb_in| replace:: `document.hldb.in`_
  .. _`document.hldb.in`: $(psource)/doc/document.hldb.in


.. [#] It is reasonable for engineering documents to link to specific source
       files.

reStructuredText References
===========================

Learning to Write reStructuredText
----------------------------------

`A ReStructuredText Primer`_:
   A Primer for ReStructuredText.  Duh...

.. _`A ReStructuredText Primer`:
   http://docutils.sourceforge.net/docs/rst/quickstart.html

`Quick reStructuredText`_:
   A cheat-sheet for reStructuredText.

.. _`Quick reStructuredText`:
   http://docutils.sourceforge.net/docs/rst/quickref.html

`reStructuredText Directives`_:
  The definitive list of the standard reStructuredText directives.

.. _`reStructuredText Directives`:
   http://docutils.sourceforge.net/spec/rst/directives.html

`reStructuredText Interpreted Text Roles`_:
  Describes the interpreted text roles implemented in the reference
  reStructuredText parser.

.. _`reStructuredText Interpreted Text Roles`:
   http://docutils.sourceforge.net/spec/rst/interpreted.html

Advanced reStructuredText Documentation
---------------------------------------

`An Introduction to reStructuredText`_:
   Answers the question, "What is reStructuredText and why did the Python
   community create it?"

.. _`An Introduction to reStructuredText`:
   http://docutils.sourceforge.net/spec/rst/introduction.html

`reStructuredText Markup Specification`_:
  The detailed technical specification; it is not a tutorial or a primer.

_`reStructuredText Markup Specification`:
  http://docutils.sourceforge.net/spec/rst/reStructuredText.html
