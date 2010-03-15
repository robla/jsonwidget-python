#!/usr/bin/python
# Library for reading JSON files according to given JSON Schema
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.

import json

from jsonwidget.jsonbase import *
from jsonwidget.jsontypes import jsontypes, get_json_type

class Error(RuntimeError):
    pass

class SchemaNode(JsonBaseNode):
    """
    Each SchemaNode instance represents one node in the data tree.  Each
    element of a child sequence (i.e. list in Python) and child map (i.e. dict
    in Python) gets its own child SchemaNode.
    """

    def __init__(self, key=None, data=None, filename=None, parent=None, 
                 ordermap=None):
        if filename is not None:
            self.filename = filename
            if data is None:
                self.load_from_file()
        else:
            self.data = data
            self.ordermap = ordermap
            self.filename = None

        # object ref for the parent
        self.parent = parent
        # local index for the node
        self.key = key
        if self.parent is None:
            self.depth = 0
            self.rootschema = self
        else:
            self.depth = self.parent.get_depth() + 1
            self.rootschema = self.parent.get_root_schema()
        if(self.data['type'] == jsontypes.OBJECT_TYPE):
            self.children = {}
            
            for subkey, subdata in self.data['mapping'].items():
                ordermap = \
                    self.ordermap['children']['mapping']['children'][subkey]
                self.children[subkey] = SchemaNode(key=subkey, data=subdata,
                                                   parent=self, 
                                                   ordermap=ordermap)
        elif(self.data['type'] == jsontypes.ARRAY_TYPE):
            ordermap = self.ordermap['children']['sequence']['children'][0]
            self.children = [SchemaNode(key=0, data=self.data['sequence'][0],
                                        parent=self, ordermap=ordermap)]

    def get_depth(self):
        return self.depth

    def get_root_schema(self):
        return self.rootschema

    def get_title(self):
        if 'title' in self.data:
            return self.data['title']
        else:
            if self.depth > 0 and self.parent.get_type() == jsontypes.ARRAY_TYPE:
                return self.parent.get_title() + " item"
            elif self.key is not None:
                return str(self.key)
            elif self.get_type() == jsontypes.ARRAY_TYPE:
                return "Array"
            else:
                return str(self.get_type())

    def set_title(self, title):
        self.data['title'] = title

    def get_type(self):
        return self.data['type']

    def _get_key_order(self):
        return self.ordermap['children']['mapping']['keys']

    def set_key_order(self, keys):
        self.ordermap['children']['mapping']['keys'] = keys

    def get_order_map(self):
        return self.ordermap

    def get_children(self):
        """
        Get a list of children, possibly ordered.  Note that even though the
        JSON spec says maps are unordered, it's pretty rude to muck with
        someone else's content ordering in a text file, and ad hoc forms
        benefit greatly from being able to control the order of elements
        """

        if(isinstance(self.children, dict)):
            return self.children.values()
        elif(isinstance(self.children, list)):
            return self.children
        else:
            raise Error("self.children has invalid type %s" %
                        type(self.children).__name__)

    def get_child(self, key):
        type = self.get_type()
        if(type == jsontypes.OBJECT_TYPE):
            return self.children[key]
        elif(type == jsontypes.ARRAY_TYPE):
            return self.children[0]
        else:
            raise Error("self.children has invalid type %s" % type)

    def get_key(self):
        return self.key

    def is_enum(self):
        return ('enum' in self.data)
        
    def is_required(self):
        return ('required' in self.data and self.data['required'])

    def enum_options(self):
        return self.data['enum']

    def get_blank_value(self):
        type = self.get_type()
        if(type == jsontypes.OBJECT_TYPE):
            retval = {}
        elif(type == jsontypes.ARRAY_TYPE):
            retval = []
        elif(type == jsontypes.INTEGER_TYPE or type == jsontypes.NUMBER_TYPE):
            retval = 0
        elif(type == jsontypes.BOOLEAN_TYPE):
            retval = False
        elif(type == jsontypes.STRING_TYPE):
            retval = ""
        else:
            retval = None
        return retval

    def dumps(self):
        retval = ""
        indent = " " * 4 
        indentlevel = self.get_depth() * 2
        if self.get_type() == jsontypes.OBJECT_TYPE:
            retval += "{\n"
            indentlevel += 1
            retval += indent * indentlevel
            retval += '"type": "%s", \n' % jsontypes.OBJECT_TYPE
            retval += indent * indentlevel
            retval += '"mapping": {'
            addcomma = False
            indentlevel += 1
            for child in self.get_children():
                if addcomma:
                    retval += ", "
                retval += "\n"
                retval += indent * indentlevel
                addcomma = True
                retval += '"%s": ' % child.get_key()
                retval += child.dumps()
                #retval += "\n"
            retval += "\n"
            indentlevel -= 1
            retval += indent * indentlevel
            retval += "}\n"
            indentlevel -= 1
            retval += indent * indentlevel
            retval += "}"
        elif self.get_type() == jsontypes.ARRAY_TYPE:
            retval += "{\n"
            indentlevel += 1
            retval += indent * indentlevel
            retval += '"type": "%s", \n' % jsontypes.ARRAY_TYPE
            retval += indent * indentlevel
            retval += '"sequence": ['
            indentlevel += 1
            addcomma = False
            for child in self.get_children():
                if addcomma:
                    retval += ","
                retval += "\n"
                retval += indent * indentlevel
                addcomma = True
                retval += child.dumps()
                #retval += "\n"
            retval += "\n"
            indentlevel -= 1
            retval += indent * indentlevel
            retval += "]\n"
            indentlevel -= 1
            retval += indent * indentlevel
            retval += "}"
        else:
            encoder = json.JSONEncoder(indent=4)
            encoder.current_indent_level = self.get_depth() * 2
            retval = encoder.encode(self.get_data())
        return retval


def generate_schema_data_from_data(jsondata):
    schema = {}

    schema['type'] = get_json_type(jsondata)

    if schema['type'] == jsontypes.OBJECT_TYPE:
        schema['mapping'] = {}
        for name in jsondata:
            schema['mapping'][name] = \
                generate_schema_data_from_data(jsondata[name])
    elif schema['type'] == jsontypes.ARRAY_TYPE:
        schema['sequence'] = [generate_schema_data_from_data(jsondata[0])]
    return schema


def generate_schema_ordermap(jsondata, jsonordermap=None):
    ordermap = {}

    datatype = get_json_type(jsondata)
    if datatype == jsontypes.OBJECT_TYPE:
        ordermap['keys'] = ['type', 'mapping']
        ordermap['children'] = {"type": {}, "mapping": {}}
        ordermap['children']['mapping'] = {"keys": [], "children": {}}
        for name in jsondata:
            ordermap['children']['mapping']['keys'].append(name)
            ordermap['children']['mapping']['children'][name] = \
                generate_schema_ordermap(jsondata[name])
        if jsonordermap is not None:
            ordermap['children']['mapping']['keys'] = jsonordermap['keys']
    elif datatype == jsontypes.ARRAY_TYPE:
        ordermap['keys'] = ['type', 'sequence']
        ordermap['children'] = {"type": {}, "sequence": {}}
        ordermap['children']['sequence'] = {"keys": [0], "children": {}}
        ordermap['children']['sequence']['children'][0] = \
            generate_schema_ordermap(jsondata[0])
    return ordermap


def generate_schema_from_data(jsondata, jsonordermap=None):
    schema = generate_schema_data_from_data(jsondata)
    ordermap = generate_schema_ordermap(jsondata, jsonordermap=jsonordermap)
    return SchemaNode(data=schema, ordermap=ordermap)

