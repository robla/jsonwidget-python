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

__version__ = "0.1.4"

def run_editor(jsonfile, schemafile=None, program_name="jsonwidget " + 
               __version__):
    """ 
    Run a simple editor with a given jsonfile and corresponding schema file.
    """
    
    if schemafile is None:
        import sys
        sys.stderr.write("Sorry, current version requires a schema")
        sys.exit(2)
    form = jsonwidget.termedit.JsonFileEditor(jsonfile=jsonfile, 
                                              schemafile=schemafile,
                                              program_name=program_name)
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

