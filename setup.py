from setuptools import setup, find_packages
import sys, os

import jsonwidget

version = jsonwidget.__version__

setup(name='jsonwidget',
      version=version,
      description="Dynamic form creation for JSON data structures from JSON schema file",
      long_description="""\
This library allows an application developer to provide a curses-based user 
interface for an application using not much more than a JSON schema.  The 
JSON schema language is described here:
http://robla.net/jsonwidget/jsonschema/

However, most people will find it much simpler to use a tool to generate a 
schema for tweaking.  The tool available here will generate a schema from an
example piece of JSON, and allow editing the resulting file:
http://robla.net/jsonwidget/example.php?sample=byexample&user=normal

This library currently only operates on a subset of JSON files, but a near-term
goal is to allow editing of any arbitrary JSON file.

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
      install_requires=["urwid",
                        "simpleparse"],
      entry_points={'console_scripts': 
                        ['jsonedit = jsonwidget.commands:jsonedit',
                         'jsonaddress = jsonwidget.commands:jsonaddress'
                        ]
                   },
      package_data={'schema':['schema/*.json']},
      )
