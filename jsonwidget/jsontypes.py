class jsontypes_v1:
    STRING_TYPE = "str"
    OBJECT_TYPE = "map"
    ARRAY_TYPE = "seq"
    BOOLEAN_TYPE = "bool"
    NUMBER_TYPE = "num"
    INTEGER_TYPE = "int"
    ANY_TYPE = "any"
    NULL_TYPE = "none"
        
class jsontypes_v2:
    STRING_TYPE = "string"
    OBJECT_TYPE = "object"
    ARRAY_TYPE = "array"
    BOOLEAN_TYPE = "boolean"
    NUMBER_TYPE = "number"
    INTEGER_TYPE = "integer"
    ANY_TYPE = "any"
    NULL_TYPE = "null"

jsontypes = jsontypes_v1


def get_json_type(data):
    """Given an arbitrary piece of data, return the type as represented in 
       json schemas."""
    if(isinstance(data, basestring)):
        return jsontypes.STRING_TYPE
    elif(isinstance(data, bool)):
        return jsontypes.BOOLEAN_TYPE
    elif(isinstance(data, int)):
        return jsontypes.INTEGER_TYPE
    elif(isinstance(data, float)):
        return jsontypes.NUMBER_TYPE
    elif(isinstance(data, dict)):
        return jsontypes.OBJECT_TYPE
    elif(isinstance(data, list)):
        return jsontypes.ARRAY_TYPE
    elif(data is None):
        return jsontypes.NULL_TYPE
    else:
        raise JsonNodeError("unknown type: %s" % type(data).__name__)

