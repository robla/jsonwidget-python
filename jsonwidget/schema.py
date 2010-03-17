#!/usr/bin/python
# Library for reading JSON files according to given JSON Schema
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.

import json

from jsonwidget.jsonbase import *
from jsonwidget.jsontypes import schemaformat, get_json_type, convert_type

class Error(RuntimeError):
    pass

class SchemaNode(JsonBaseNode):
    """
    Each SchemaNode instance represents one node in the data tree.  Each
    element of a child sequence (i.e. list in Python) and child map (i.e. dict
    in Python) gets its own child SchemaNode.
    """

    def __init__(self, key=None, data=None, filename=None, parent=None, 
                 ordermap=None, fmt=schemaformat):
        properties_id = fmt.idmap['properties']
        items_id = fmt.idmap['items']
        self.schemaformat = fmt
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
        if(self.data['type'] == fmt.typemap['object']):
            self.children = {}
            
            for subkey, subdata in self.data[properties_id].items():
                ordermap = \
                    self.ordermap['children'][properties_id]['children'][subkey]
                self.children[subkey] = SchemaNode(key=subkey, data=subdata,
                                                   parent=self, 
                                                   ordermap=ordermap)
        elif(self.data['type'] == fmt.typemap['array']):
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
            if self.depth > 0 and self.parent.is_type('array'):
                return self.parent.get_title() + " item"
            elif self.key is not None:
                return str(self.key)
            elif self.is_type('array'):
                return "Array"
            else:
                return str(self.get_type())

    def set_title(self, title):
        self.data['title'] = title

    def get_type(self):
        return self.data['type']
    
    def get_format(self):
        return self.schemaformat

    def is_type(self, cmptype):
        return self.get_type() == self.schemaformat.typemap[cmptype]

    def _get_key_order(self):
        properties_id = schemaformat.idmap['properties']
        return self.ordermap['children'][properties_id]['keys']

    def set_key_order(self, keys):
        properties_id = schemaformat.idmap['properties']
        self.ordermap['children'][properties_id]['keys'] = keys

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
        if(self.is_type('object')):
            return self.children[key]
        elif(self.is_type('array')):
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
        if(self.is_type('object')):
            retval = {}
        elif(self.is_type('array')):
            retval = []
        elif(self.is_type('integer') or self.is_type('number')):
            retval = 0
        elif(self.is_type('boolean')):
            retval = False
        elif(self.is_type('string')):
            retval = ""
        else:
            retval = None
        return retval

    def convert(self, newfmt):
        if(self.is_type('object') or self.is_type('array')):
            for child in self.get_children():
                child.convert(newfmt)
        self.data['type'] = convert_type(oldtype=self.data['type'], 
                                         oldfmt=self.schemaformat,
                                         newfmt=newfmt)
        self.schemaformat = newfmt

    def dumps(self):
        retval = ""
        indent = " " * 4 
        indentlevel = self.get_depth() * 2
        if self.is_type('object'):
            retval += "{\n"
            indentlevel += 1
            retval += indent * indentlevel
            retval += '"type": "%s", \n' % self.schemaformat.typemap['object']
            retval += indent * indentlevel
            retval += '"%s": {' % self.schemaformat.idmap['properties']
            addcomma = False
            indentlevel += 1
            for key in self._get_key_order():
                if addcomma:
                    retval += ", "
                retval += "\n"
                retval += indent * indentlevel
                addcomma = True
                retval += '"%s": ' % key
                retval += self.get_child(key).dumps()
                #retval += "\n"
            retval += "\n"
            indentlevel -= 1
            retval += indent * indentlevel
            retval += "}\n"
            indentlevel -= 1
            retval += indent * indentlevel
            retval += "}"
        elif self.is_type('array'):
            retval += "{\n"
            indentlevel += 1
            retval += indent * indentlevel
            retval += '"type": "%s", \n' % self.schemaformat.typemap['array']
            retval += indent * indentlevel
            retval += '"%s": [' %  self.schemaformat.idmap['items']
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


def generate_schema_data_from_data(jsondata, fmt=schemaformat):
    schema = {}
    properties_id = fmt.idmap['properties']
    items_id = fmt.idmap['items']

    schema['type'] = get_json_type(jsondata)

    if schema['type'] == fmt.typemap['object']:
        schema[properties_id] = {}
        for name in jsondata:
            schema[properties_id][name] = \
                generate_schema_data_from_data(jsondata[name])
    elif schema['type'] == fmt.typemap['array']:
        schema[items_id] = [generate_schema_data_from_data(jsondata[0])]
    return schema


def generate_schema_ordermap(jsondata, jsonordermap=None, fmt=schemaformat):
    ordermap = {}
    properties_id = schemaformat.idmap['properties']
    items_id = schemaformat.idmap['items']

    datatype = get_json_type(jsondata)
    if datatype == fmt.typemap['object']:
        ordermap['keys'] = ['type', properties_id]
        ordermap['children'] = {"type": {}, properties_id: {}}
        ordermap['children'][properties_id] = {"keys": [], "children": {}}
        for name in jsondata:
            ordermap['children'][properties_id]['keys'].append(name)
            if jsonordermap is None:
                childmap = None
            else:
                childmap = jsonordermap['children'][name]
            ordermap['children'][properties_id]['children'][name] = \
                generate_schema_ordermap(jsondata[name], jsonordermap=childmap)
        if jsonordermap is not None:
            ordermap['children'][properties_id]['keys'] = jsonordermap['keys']
    elif datatype == fmt.typemap['array']:
        ordermap['keys'] = ['type', items_id]
        ordermap['children'] = {"type": {}, items_id: {}}
        ordermap['children'][items_id] = {"keys": [0], "children": {}}
        if jsonordermap is None:
            childmap = None
        else:
            childmap = jsonordermap['children'][0]
        ordermap['children'][items_id]['children'][0] = \
            generate_schema_ordermap(jsondata[0], jsonordermap=childmap)
    return ordermap


def generate_schema_from_data(jsondata, jsonordermap=None, fmt=schemaformat):
    schema = generate_schema_data_from_data(jsondata, fmt=fmt)
    ordermap = generate_schema_ordermap(jsondata, jsonordermap=jsonordermap,
                                        fmt=fmt)
    return SchemaNode(data=schema, ordermap=ordermap, fmt=fmt)

