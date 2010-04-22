from setuptools import setup, find_packages
import sys, os

version = '0.1.7'

setup(name='jsonwidget',
      version=version,
      description="jsonwidget is a general-purpose JSON validation and \
manipulation, and form-building library for terminal windows and web pages",
      long_description="""\
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

Website: http://robla.net/jsonwidget""",
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=["Development Status :: 3 - Alpha",
                   "Environment :: Console :: Curses",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: POSIX",
                   "Programming Language :: Python :: 2.4",
                   "Programming Language :: Python :: 2.5",
                   "Programming Language :: Python :: 2.6",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   "Topic :: Software Development :: User Interfaces",
                   "Topic :: Text Editors"], 
      keywords='json form',
      author='Rob Lanphier',
      author_email='robla@robla.net',
      url='http://robla.net/jsonwidget',
      license='BSD',
      packages=['jsonwidget'],
      include_package_data=True,
      zip_safe=False,
      install_requires=["simpleparse"],
      extras_require = {"console":["urwid"]},
      entry_points={},
      scripts=['jsonedit', 'jsonaddress', 'csvedit', 'jwc'],
      package_data={'schema':['jsonwidget/schema/*.json']},
      )
