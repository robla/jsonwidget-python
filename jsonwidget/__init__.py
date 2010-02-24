"""
Library for generating a user interface from a JSON schema.

This library allows an application developer to provide a curses-based user 
interface for an application using not much more than a JSON schema.  The 
current JSON schema is a subset of the Kwalify syntax described here:
http://www.kuwata-lab.com/kwalify/ruby/users-guide.01.html#schema

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

def run_editor(jsonfile, schemafile=None):
    """ 
    Run a simple editor with a given jsonfile and corresponding schema file.
    """
    
    if schemafile is None:
        import sys
        sys.stderr.write("Sorry, current version requires a schema")
        sys.exit(2)
    form = jsonwidget.termedit.JsonEditor(jsonfile=jsonfile, 
                                          schemafile=schemafile,
                                          program_name="jsonedit 0.1pre")
    form.run()


