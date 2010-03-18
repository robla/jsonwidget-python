class schemaformat_v1:
    version = 1
    typemap = {"string":"str",
               "object":"map",
               "array":"seq",
               "boolean":"bool",
               "number":"number",
               "integer":"int",
               "any":"any",
               "null":"none"}
    typemap_rev = dict([(typemap[key], key) for key in typemap])
    idmap = {"properties":"mapping",
             "items":"sequence"}

class schemaformat_v2:
    version = 2
    typemap = {"string":"string",
               "object":"object",
               "array":"array",
               "boolean":"boolean",
               "number":"number",
               "integer":"integer",
               "any":"any",
               "null":"null"}
    typemap_rev = dict([(typemap[key], key) for key in typemap])
    idmap = {"properties":"properties",
             "items":"items"}

schemaformat = schemaformat_v1


def get_json_type(data, fmt=schemaformat):
    """Given an arbitrary piece of data, return the type as represented in 
       json schemas."""
    if(isinstance(data, basestring)):
        return fmt.typemap['string']
    elif(isinstance(data, bool)):
        return fmt.typemap['boolean']
    elif(isinstance(data, int)):
        return fmt.typemap['integer']
    elif(isinstance(data, float)):
        return fmt.typemap['number']
    elif(isinstance(data, dict)):
        return fmt.typemap['object']
    elif(isinstance(data, list)):
        return fmt.typemap['array']
    elif(data is None):
        return fmt.typemap['null']
    else:
        raise JsonNodeError("unknown type: %s" % type(data).__name__)


def convert_type(oldtype=None, oldfmt=schemaformat_v1, newfmt=schemaformat_v2):
    return newfmt.typemap[oldfmt.typemap_rev[oldtype]]


