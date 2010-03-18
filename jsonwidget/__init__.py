"""
Library for generating a user interface from a JSON schema.

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

Usage:
    import jsonwidget
    
    foo = "foo.json"
    fooschema = "fooschema.json"
    jsonwidget.run_editor(foo, schemafile=fooschema)


Website: http://robla.net/jsonwidget
"""

import jsonwidget.termedit
import os

from jsontypes import schemaformat

__version__ = "0.1.5"

def run_editor(jsonfile, schemafile=None, schemaobj=None, 
               program_name="jsonwidget " + __version__):
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
