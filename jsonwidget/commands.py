#!/usr/bin/python -tt
# jsonedit - urwid-based JSON editor
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.

import optparse
import sys
import jsonwidget


def jsonedit():
    '''urwid-based JSON editor'''
    usage = "usage: %prog [options] arg"
    parser = optparse.OptionParser(usage)
    defschema = jsonwidget.find_system_schema("datatype-example-schema.json")
 
    parser.add_option("-s", "--schema", dest="schema",
                      default=defschema,
                      help="use this schema to build the form")
    parser.add_option("--tracebacks", dest="tracebacks",
                      default=False,
                      help="See full tracebacks")
    (options, args) = parser.parse_args()
    if not options.tracebacks:
        sys.tracebacklimit = 1000

    if len(args) > 1:
        parser.error("Too many arguments." +
                     "  Just one .json file at a time, please.")
    if len(args) == 1:
        jsonfile = args[0]
    else:
        jsonfile = None
    progname = "jsonedit " + jsonwidget.__version__
    jsonwidget.run_editor(jsonfile, schemafile=options.schema, 
                          program_name=progname)


def jsonaddress():
    '''urwid-based JSON address book editor'''
    usage = "usage: %prog [options] arg"
    parser = optparse.OptionParser(usage)
    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error("Too many arguments." +
                     "  Just one adddressbook file at a time, please.")
    if len(args) == 1:
        addressbook = args[0]
    else:
        addressbook = None

    defschema = jsonwidget.find_system_schema("addressbookschema.json")
    progname = "jsonaddress " + jsonwidget.__version__
    jsonwidget.run_editor(addressbook, schemafile=defschema,
                          program_name=progname)


if __name__ == "__main__":
    jsonedit()

