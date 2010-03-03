from setuptools import setup, find_packages
import sys, os

version = '0.1.1'

setup(name='jsonwidget',
      version=version,
      description="Dynamic form creation for JSON data structures from JSON schema file",
      long_description="""\
The jsonwidget libraries are a set of libraries implementing a form interface 
for editing editing arbitrary JSON files. Implementations so far:
* jsonwidget-python: A terminal window implementation suitable for editing 
  forms via ssh or in a local terminal window.
* jsonwidget-javascript: A client-side Javascript library generates a basic 
  HTML form interface in the browser
Application designers using one of these libraries have the option of 
providing a schema, limiting the input to a subset of valid JSON compatible 
with whatever application is actually consuming the JSON, or using a provided 
permissive schema that allows any valid JSON. The libraries are capable of 
dynamically generating a form is dynamically generated using nothing more than 
a schema and a JSON file as input.

The libraries are licensed under a BSD-style license, making the licensing very
flexible for many different applications.""",
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
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=["urwid",
                        "simpleparse"],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
