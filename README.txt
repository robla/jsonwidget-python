==========
jsonwidget
==========

Introduction
------------
jsonwidget is a general-purpose JSON validation and manipulation library.  This 
library provides the following functions for applications:

*  Validation of JSON-compatible data against a schema
*  Automatic generation of a schema from JSON-compatible data
*  Construction of a curses-based tree data editing user interface from a schema
*  Construction of a Javascript-based web tree data editing user interface 
   from a schema
*  Simple WSGI server to serve the web user interface, and validate and store 
   result of editing with the web user interface

Though jsonwidget is optimized for working with JSON, it is useful for 
providing editing capability for any JSON-compatible data structure.

Included utilities
------------------

The following utilities are included with jsonwidget:

* jsonedit - A terminal-based application (like you would use via SSH or 
  local terminal on Linux and Mac). It's based on urwid, an excellent 
  Python-based library for building terminal-based user interfaces.
* csvedit - A variation on jsonedit that allows editing of .csv/tsv files.
* jsonaddress - an example JSON address book editor
* jwc - a command line utility with the following functions:

  * editserver - launch a web server to edit a json file from a browser
  * json2yaml - convert a json file to yaml with comments pulled from schema 
    (also yaml2json to go back)
  * schemagen - create a schema from an example json file
  * validate - validate a JSON file against a schema

Using the jsonwidget library
----------------------------
A good example (as of this writing) of how to use jsonwidget as a library is 
"yamledit" in the examples directory, which demonstrates where to hook in file
parsers for formats other than JSON.

Schema language
---------------
There are two JSON schema languages that are supported by jsonwidget:

*  Version 1 is broadly supported by the library, and is documented here:
   `Version 1 JSON Schema documentation`__
__ http://robla.net/jsonwidget/jsonschema/
   
*  Version 2 is a subset of the JSON schema format documented here:
   http://json-schema.org/
   
   Version 2 is not fully supported by jsonwidget at this time.  The Python 
   portions of the library support v1 and v2 equally well (more or less), but 
   the Javascript portion only supports v1.

License
-------
Most of jsonwidget is licensed under the BSD license.  Portions were
derived from urwid, and thus are LGPL.  Copies of both licenses can 
be found in the docs directory.

Unless otherwise indicated, all files in this distribution are under the
following license (BSD).

Reporting Bugs
--------------
Please send bug reports to me (Rob Lanphier <robla@robla.net>), or file a bug
at the `bug tracker`__

__ http://bitbucket.org/robla/jsonwidget-python/issues

Contributing
------------
The `latest source`__ can be found at Bitbucket.

__ http://bitbucket.org/robla/jsonwidget-python/


Website
-------
http://jsonwidget.org


