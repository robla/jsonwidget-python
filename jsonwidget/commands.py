#!/usr/bin/python -tt
# jsonedit - urwid-based JSON editor
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under 3-clause BSD license.  See LICENSE.txt for details.

import optparse
import os
import sys
import jsonwidget

from jsonwidget.jsonnode import JsonNodeError
from jsontypes import schemaformat

def jsonedit():
    '''urwid-based JSON editor'''
    usage = "usage: %prog [options] arg"
    parser = optparse.OptionParser(usage)
    defschema = find_system_schema("datatype-example-schema.json")
 
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


def run_editor(jsonfile, schemafile=None, schemaobj=None, 
               program_name="jsonwidget " + jsonwidget.__version__):
    """ 
    Run a simple editor with a given jsonfile and corresponding schema file.
    """
    
    form = jsonwidget.termedit.JsonFileEditor(jsonfile=jsonfile, 
                                              schemafile=schemafile,
                                              schemaobj=schemaobj,
                                              program_name=program_name)
    if schemafile is None:
        form.set_startup_notification(
            'Using schema derived from json file.  Use "--schema" at startup to provide custom schema')
    form.run()


def find_system_schema(schemaname):
    """
    Resolve schemaname to a full path.  This allows referencing
    one of the bundled schemas without spelling out the full path.
    """
    # TODO: implement schemapath config variable.
    try:
        import pkg_resources
    except ImportError:
        filename = os.path.join("jsonwidget", "schema", schemaname)
    else:
        filename = os.path.join("schema", schemaname)
        filename = pkg_resources.resource_filename("jsonwidget", 
            filename)
    return filename


def generate_schema(filename=None, data=None, jsonstring=None, 
                    version=schemaformat.version):
    """
    Generate a schema from a JSON example.
    """
    import json
    import jsonwidget.jsonorder
    if filename is not None:
        with open(filename, 'r') as f:
            jsonbuffer = f.read()
        jsondata = json.loads(jsonbuffer)
        jsonordermap = \
            jsonwidget.jsonorder.JsonOrderMap(jsonbuffer).get_order_map()
        return jsonwidget.schema.generate_schema_from_data(jsondata, 
            jsonordermap=jsonordermap, version=version)
    else:
        raise RuntimeError("only filename-based generation is supported")


def upgradeschema(args):
    usage = """\
Create a version 2 schema from a version 1 schema
usage: %prog upgradeschema oldschema\
"""
    subparser = optparse.OptionParser(usage=usage)
    (options, subargs) = subparser.parse_args(args[1:])
    if len(subargs)==1:
        import jsonwidget.schema
        import jsonwidget.jsontypes
    
        schemanode = jsonwidget.schema.SchemaNode(filename=subargs[0])
        schemanode.convert(jsonwidget.jsontypes.schemaformat_v2)
        print schemanode.dumps()
        sys.exit(0)
    elif len(subargs)<1:
        subparser.error("old schema file required")
    else:
        subparser.error("only one file at a time")


def schemagen(args):
    usage = """\
Create a schema from an example json file
usage: %prog schemagen [options] jsonfile\
"""
    subparser = optparse.OptionParser(usage=usage)
    versionhelp = "schema format version to use.  Default: %i" % \
                    schemaformat.version
    subparser.add_option("-v", "--version", dest="version", type="int",
                            default=schemaformat.version,
                            help=versionhelp)
    (options, subargs) = subparser.parse_args(args[1:])
    if len(subargs)==1:
        schemaobj = jsonwidget.generate_schema(subargs[0], 
                                                version=options.version)
        print schemaobj.dumps()
        sys.exit(0)
    elif len(subargs)<1:
        subparser.error("jsonfile required")
    else:
        subparser.error("only one file at a time")


def json2yaml(args):
    import jsonwidget.yamltools
    usage = """\
Convert a file from json to yaml, pulling in comments from the given schema if
one is provided.
usage: %prog json2yaml [options] jsonfile\
"""
    subparser = optparse.OptionParser(usage=usage)
    schemahelp = "schema format version to use.  Default: None"
    subparser.add_option("-s", "--schema", dest="schema", type="str",
                            default=None,
                            help=schemahelp)
    (options, subargs) = subparser.parse_args(args[1:])

    if len(subargs)==1:
        schemafile = options.schema
        schemaobj = None

        if schemafile is None:
            schemaobj = jsonwidget.generate_schema(subargs[0])
        jsonobj = jsonwidget.jsonnode.JsonNode(filename=subargs[0], 
                                                schemafile=schemafile,
                                                schemanode=schemaobj)
        print jsonwidget.yamltools.jsonnode_to_yaml(jsonobj)
        sys.exit(0)
    elif len(subargs)<1:
        subparser.error("jsonfile required")
    else:
        subparser.error("only one file at a time")


def yaml2json(args):
    import json
    import yaml

    usage = """\
Convert a file from yaml to json.
usage: %prog yaml2json [options] yamlfile\
"""
    subparser = optparse.OptionParser(usage=usage)
    (options, subargs) = subparser.parse_args(args[1:])

    fp = open(subargs[0])
    foo = yaml.load(fp)
    fp.close()
    print json.dumps(foo, indent=4, sort_keys=True)


def json2plist(args):
    import json
    import plistlib

    usage = """\
Convert a file from json to plist.
usage: %prog json2plist [options] jsonfile\
"""
    subparser = optparse.OptionParser(usage=usage)
    (options, subargs) = subparser.parse_args(args[1:])

    fp = open(subargs[0])
    jsondata = json.load(fp)
    fp.close()
    
    print plistlib.writePlistToString(jsondata)


def json2xmlrpc(args):
    import json
    import xmlrpclib
    import xml.dom.minidom

    usage = """\
Convert a file from json to xmlrpc.
usage: %prog json2plist [options] jsonfile\
"""
    subparser = optparse.OptionParser(usage=usage)
    (options, subargs) = subparser.parse_args(args[1:])

    fp = open(subargs[0])
    jsondata = json.load(fp)
    fp.close()
    print xmlrpclib.dumps(('data',jsondata))
    #print xml.dom.minidom.parseString(text).toprettyxml(indent='  ')


def plist2json(args):
    import json
    import plistlib

    usage = """\
Convert a file from json to plist.
usage: %prog plist2json [options] plistfile\
"""
    subparser = optparse.OptionParser(usage=usage)
    (options, subargs) = subparser.parse_args(args[1:])

    plistdata = plistlib.readPlist(subargs[0])
    print json.dumps(plistdata, indent=4, sort_keys=True)


def validate(args):
    import json
    import sys

    usage = """\
Validate a JSON file against a schema.
usage: %prog validate [options] jsonfile\
"""
    schemafile = jsonwidget.find_system_schema("openschema.json")
    subparser = optparse.OptionParser(usage=usage)
    schemahelp = "schema format version to use.  Default: %s" % schemafile
    subparser.add_option("-s", "--schema", dest="schema", type="str",
                            default=schemafile,
                            help=schemahelp)
    (options, subargs) = subparser.parse_args(args[1:])
    if len(subargs)==1:
        try:
            jsonwidget.jsonnode.JsonNode(filename=subargs[0], 
                                            schemafile=options.schema)
            print "Valid file!  " + subargs[0] + \
                " validates against " + options.schema
        except jsonwidget.jsonnode.JsonNodeError as inst:
            print str(inst)
            sys.exit(1)
    elif len(subargs)<1:
        subparser.error("jsonfile required")
    else:
        subparser.error("only one file at a time")


def editserver(args):
    import json
    import sys
    from jsonwidget.server.wsgieditserver import start_server

    usage = """\
Launch a web server which serves a Javascript-based JSON editor for a single \
file.
usage: %prog editserver [options] jsonfile\
"""

    schemafile = jsonwidget.find_system_schema("openschema.json")
    subparser = optparse.OptionParser(usage=usage)
    schemahelp = "schema format version to use.  Default: %s" % schemafile
    subparser.add_option("-s", "--schema", dest="schema", type="str",
                            default=schemafile,
                            help=schemahelp)
    (options, subargs) = subparser.parse_args(args[1:])

    if len(subargs)==1:
        start_server(jsonfile=subargs[0], schemafile=options.schema)
    elif len(subargs)<1:
        subparser.error("jsonfile required")
    else:
        subparser.error("only one file at a time")


if __name__ == "__main__":
    jsonedit()

