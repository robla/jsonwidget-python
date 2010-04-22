"""
Library for generating a user interface from a JSON schema.

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


Usage:
    import jsonwidget
    
    foo = "foo.json"
    fooschema = "fooschema.json"
    jsonwidget.run_editor(foo, schemafile=fooschema)


Website: http://robla.net/jsonwidget
"""

__version__ = "0.1.7"

__author__ = 'Rob Lanphier <robla@robla.net>'

# using __all__ for doc purposes only
__all__ = ['TreeFileDatatype', 'TreeFileWrapper']

from termedit import JsonFileEditor, JsonPinotFile, TreeFileDatatype, \
    TreeFileWrapper
from schema import generate_schema_from_data


from jsontypes import schemaformat

from jsonnode import JsonNodeError

from commands import jsonedit, upgrade_schema, run_editor, find_system_schema,\
    generate_schema




