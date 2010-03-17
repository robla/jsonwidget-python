#!/usr/bin/python -tt
# jsonedit - urwid-based JSON editor
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.

import optparse
import sys
import jsonwidget

from jsonwidget.jsonnode import JsonNodeError

def jsonedit():
    '''urwid-based JSON editor'''
    usage = "usage: %prog [options] arg"
    parser = optparse.OptionParser(usage)
    defschema = jsonwidget.find_system_schema("datatype-example-schema.json")
 
    parser.add_option("-s", "--schema", dest="schema",
                      default=None,
                      help="use this schema to build the form")
    parser.add_option("--tracebacks", dest="tracebacks",
                      default=False,
                      help="See full tracebacks")
    parser.add_option("--schemagen", dest="schemagen", action="store_true",
                      default=False,
                      help="Print generated schema to standard output and exit")
    
    (options, args) = parser.parse_args()
    if not options.tracebacks:
        sys.tracebacklimit = 1000

    schemafile = options.schema
    schemaobj = None

    if len(args) > 1:
        parser.error("Too many arguments." +
                     "  Just one .json file at a time, please.")
    if len(args) == 1:
        jsonfile = args[0]
        if schemafile is None:
            schemaobj = jsonwidget.generate_schema(jsonfile)
    else:
        jsonfile = None
        if schemafile is None:
            schemafile = defschema

    if options.schemagen == True:
        if jsonfile is None:
            parser.error("JSON-formatted required with --schemagen")
        schemaobj = jsonwidget.generate_schema(jsonfile)
        print schemaobj.dumps()
        sys.exit(0)

    progname = "jsonedit " + jsonwidget.__version__
    try:
        jsonwidget.run_editor(jsonfile, schemafile=schemafile, schemaobj=schemaobj,
                              program_name=progname)
    except JsonNodeError as inst:
        sys.stderr.writelines(parser.get_prog_name() + " error:\n")
        sys.stderr.writelines(str(inst) + "\n")
        if schemafile is None:
            print "  Try using --schemagen to generate a schema, edit it to " +\
                "add valid keys, then relaunch with --schema\n"
        sys.exit(2)


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
    try:
        jsonwidget.run_editor(addressbook, schemafile=defschema,
                              program_name=progname)
    except JsonNodeError as inst:
        sys.stderr.writelines(parser.get_prog_name() + " error:\n")
        sys.stderr.writelines(str(inst) + "\n\n")
        sys.exit(2)

def upgrade_schema(filename):
    import jsonwidget.schema
    import jsonwidget.jsontypes
    
    schemanode = jsonwidget.schema.SchemaNode(filename=filename)
    schemanode.convert(jsonwidget.jsontypes.schemaformat_v2)
    print schemanode.dumps()

if __name__ == "__main__":
    jsonedit()

