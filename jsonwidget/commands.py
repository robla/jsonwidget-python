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
    parser.add_option("-s", "--schema", dest="schema",
                      default="schema/datatype-example-schema.json",
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
    jsonwidget.run_editor(jsonfile, schemafile=options.schema, 
                          program_name="jsonedit 0.1")


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
    jsonwidget.run_editor(addressbook, 
                          schemafile="schema/addressbookschema.json",
                          program_name="jsonaddress 0.1")


if __name__ == "__main__":
    jsonedit()

