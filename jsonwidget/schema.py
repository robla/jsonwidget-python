#!/usr/bin/python
# Library for reading JSON files according to given JSON Schema
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.

import json

from jsonwidget.jsonbase import *

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
        if(self.data['type'] == 'map'):
            self.children = {}
            
            for subkey, subdata in self.data['mapping'].items():
                ordermap = \
                    self.ordermap['children']['mapping']['children'][subkey]
                self.children[subkey] = SchemaNode(key=subkey, data=subdata,
                                                   parent=self, 
                                                   ordermap=ordermap)
        elif(self.data['type'] == 'seq'):
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
            if self.depth > 0 and self.parent.get_type() == 'seq':
                return self.parent.get_title()
            else:
                return str(self.key)

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
        if(type == 'map'):
            return self.children[key]
        elif(type == 'seq'):
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
        if(type == 'map'):
            retval = {}
        elif(type == 'seq'):
            retval = []
        elif(type == 'int' or type == 'number'):
            retval = 0
        elif(type == 'bool'):
            retval = False
        elif(type == 'str'):
            retval = ""
        else:
            retval = None
        return retval


def generate_schema_from_data(jsondata):
    schema = {}
    ordermap = {}

    schema['type'] = get_json_type(jsondata)

    if schema['type'] == 'map':
        schema['mapping'] = {}
        ordermap['keys'] = ['type', 'mapping']
        ordermap['children'] = {"type": {}, "mapping": {}}
        ordermap['children']['mapping'] = {"keys": [], "children": {}}
        for name in jsondata:
            schemaobj = generate_schema_from_data(jsondata[name])
            schema['mapping'][name] = schemaobj.get_data()
            ordermap['children']['mapping']['keys'].append(name)
            ordermap['children']['mapping']['children'][name] = schemaobj.get_order_map()
    elif schema['type'] == 'seq':
        schemaobj = generate_schema_from_data(jsondata[0])
        schema['sequence'] = [schemaobj.get_data()]
        ordermap['keys'] = ['type', 'sequence']
        ordermap['children'] = {"type": {}, "sequence": {}}
        ordermap['children']['sequence'] = {"keys": [0], "children": {}}
        ordermap['children']['sequence']['children'][0] = schemaobj.get_order_map()

    return SchemaNode(data=schema, ordermap=ordermap)

