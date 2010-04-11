#!/usr/bin/python
# Library for reading JSON files according to given JSON Schema
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.

import json

from jsonwidget.jsonbase import *
from jsonwidget.jsontypes import schemaformat, schemaformat_v1, \
    schemaformat_v2, get_json_type, convert_type

class JsonSchemaError(RuntimeError):
    pass



class SchemaNode(JsonBaseNode):
    """
    Each SchemaNode instance represents one node in the data tree.  Each
    element of a child sequence (i.e. list in Python) and child map (i.e. dict
    in Python) gets its own child SchemaNode.
    """

    def __init__(self, key=None, data=None, filename=None, parent=None, 
                 ordermap=None, fmt=None, isaddedprop=False):

        if filename is not None:
            self.filename = filename
            if data is None:
                self.load_from_file()
        else:
            self.data = data
            self.ordermap = ordermap
            self.filename = None

        if fmt is not None:
            self.schemaformat = fmt
        elif parent is not None:
            self.schemaformat = parent.get_format()
        elif self.data['type'] in ['object', 'array']:
            self.schemaformat = schemaformat_v2
        else:
            self.schemaformat = schemaformat_v1

        fmt = self.schemaformat
        properties_id = fmt.idmap['properties']
        items_id = fmt.idmap['items']

        self.is_added_prop = isaddedprop

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

        self._register_fragment_id()

        if(self.data['type'] == fmt.typemap['object']):
            self.children = {}
            
            for subkey, subdata in self.data[properties_id].items():
                ordermap = \
                    self.ordermap['children'][properties_id]['children'][subkey]

                if (self.schemaformat.version == 1 and 
                    'user_key' in self.data and
                    subkey == self.data['user_key']):
                    isaddedprop = True
                else:
                    isaddedprop = False

                self.children[subkey] = SchemaNode(key=subkey, data=subdata,
                                                   parent=self, 
                                                   ordermap=ordermap,
                                                   isaddedprop=isaddedprop)
        elif(self.data['type'] == fmt.typemap['array']):
            if fmt.version == 1:
                ordermap = self.ordermap['children'][items_id]['children'][0]
                self.children = [SchemaNode(key=0, data=self.data[items_id][0],
                                            parent=self, ordermap=ordermap)]
            elif fmt.version == 2:
                ordermap = self.ordermap['children'][items_id]['children'][0]
                self.children = [SchemaNode(key=0, data=self.data[items_id][0],
                                            parent=self, ordermap=ordermap)]

    def _register_fragment_id(self):
        """
        If this schema node has a globally addressable id, then register 
        it with the root schema.  This probably only makes sense with v1 
        schemas.
        """
        if self.schemaformat.version == 1 and 'id' in self.data:
            root = self.get_root_schema()
            root._store_node_as_id(self, self.data['id'])

    def _store_node_as_id(self, node, id):
        """
        Add node to global id index
        """
        try:
            self._node_index[id]=node
        except AttributeError:
            self._node_index={id:node}

    def _get_node_by_id(self, id):
        try:
            return self._node_index[id]
        except KeyError, AttributeError:
            return None
    
    def resolve_fragment_id(self):
        """ if this is a fragment ref/idref, return the target schema node """
        return self.get_root_schema()._get_node_by_id(self.data['idref'])

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

    def get_description(self):
        if 'description' in self.data:
            return self.data['description']
        else:
            return ''

    def get_type(self):
        return self.data['type']
    
    def get_format(self):
        return self.schemaformat

    def is_type(self, cmptype):
        return self.get_type() == self.schemaformat.typemap[cmptype]

    def _get_key_order(self):
        properties_id = self.schemaformat.idmap['properties']
        return self.ordermap['children'][properties_id]['keys']

    def set_key_order(self, keys):
        properties_id = self.schemaformat.idmap['properties']
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
            raise JsonSchemaError("self.children has invalid type %s" %
                                  type(self.children).__name__)

    def get_child(self, key):
        if(self.is_type('object')):
            try:
                return self.children[key]
            except KeyError:
                if(self.allow_additional_properties()):
                    return self.get_additional_props_node()
                else:
                    raise
        elif(self.is_type('array')):
            return self.children[0]
        else:
            raise JsonSchemaError("self.children has invalid type %s" % type)

    def get_key(self):
        return self.key

    def is_enum(self):
        return ('enum' in self.data)
        
    def is_required(self):
        if self.schemaformat.version == 1:
            return ('required' in self.data and self.data['required'])
        if self.schemaformat.version == 2:
            if 'optional' in self.data:
                return not self.data['optional']
            else:
                return False
        else:
            raise JsonSchemaError("unhandled schema format")

    def allow_additional_properties(self):
        if self.schemaformat.version == 1:
            return 'user_key' in self.data
        elif self.schemaformat.version == 2:
            if 'additionalProperties' in self.data:
                return not self.data['additionalProperties'] == False
            else:
                return True
        else:
            raise JsonSchemaError("unhandled schema format")

    def get_additional_props_node(self):
        if self.allow_additional_properties():
            if self.schemaformat.version == 1:
                userkey = self.data['user_key']
                propdata = self.data['mapping'][userkey]
                ordermap = \
                    self.ordermap['children']['mapping']['children'][userkey]
                self.additional_props = SchemaNode(data=propdata, parent=self, 
                                                   ordermap=ordermap, 
                                                   key=userkey,
                                                   isaddedprop=True)
                return self.additional_props
            elif self.schemaformat.version == 2:
                return self.get_additional_props_node_v2()
            else:
                raise JsonSchemaError("unhandled schema format")
        else:
            raise JsonSchemaError("additional properties not allowed")

    def get_additional_props_node_v2(self):
        if not hasattr(self, 'additional_props'):
            if 'additionalProperties' in self.data:
                propdata = self.data['additionalProperties']
                ordermap = self.ordermap['children']['additionalProperties']
            else:
                propdata = {}
                ordermap = {'keys':[], 'children':{}}
            self.additional_props = SchemaNode(data=propdata, parent=self, 
                                               ordermap=ordermap,
                                               isaddedprop=True)
        return self.additional_props
        
    def is_additional_props_node(self):
        return self.is_added_prop

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



    def convert_types(self, newfmt):
        if self.is_type('object'):
            old_child_id = self.schemaformat.idmap['properties']
            new_child_id = newfmt.idmap['properties']
        if self.is_type('array'):
            old_child_id = self.schemaformat.idmap['items']
            new_child_id = newfmt.idmap['items']
        if self.is_type('object') or self.is_type('array'):
            for child in self.get_children():
                child.convert(newfmt)
            self.data[new_child_id] = self.data[old_child_id]
            del self.data[old_child_id]
            self.ordermap['children'][new_child_id] = \
                self.ordermap['children'][old_child_id]
            del self.ordermap['children'][old_child_id]

        self.data['type'] = convert_type(oldtype=self.data['type'], 
                                         oldfmt=self.schemaformat,
                                         newfmt=newfmt)

    def convert(self, newfmt):
        # this stuff is all very specific to v1->v2 conversion, which is
        # unfortunate, because the calling convention implies much more 
        # flexibility
        if self.is_type('object'):
            propkey = self.schemaformat.idmap['properties']
            if self.allow_additional_properties():
                userkey = self.data['user_key']
                self.data['additionalProperties'] = \
                    self.data[propkey][userkey]
                del self.data['user_key']
                del self.data[propkey][userkey]
                self.ordermap['children']['additionalProperties'] = \
                    self.ordermap['children']['mapping']['children'][userkey]
                del self.ordermap['children']['mapping']['children'][userkey]
                self.ordermap['children']['mapping']['keys'].remove(userkey)
            else:
                self.data['additionalProperties'] = False

        self.convert_types(newfmt)
        self.data['optional'] = not self.is_required()
        if 'required' in self.data:
            del self.data['required']
        self.schemaformat = newfmt

    def dumps(self, indentlevel=None):
        """ Version of dumps that more or less respects the originally-written
            key order."""
        encoder = json.JSONEncoder(indent=4)
        retval = ""
        indent = " " * 4
        if indentlevel is None:
            indentlevel = self.get_depth() * 2
        if self.is_additional_props_node():
            indentlevel -= 1

        if self.is_type('object') or self.is_type('array'):
            retval += "{\n"
            indentlevel += 1
            data = self.get_data()
            props = sorted(data.keys())
            if self.is_type('object'):
                props.remove(self.schemaformat.idmap['properties'])
                if(self.schemaformat.version == 2 and 
                   'additionalProperties' in props):
                    props.remove('additionalProperties')
                for prop in props:
                    retval += indent * indentlevel
                    encprop = encoder.encode(prop)
                    val = encoder.encode(data[prop])
                    retval += '%s: %s, \n' % (encprop, val)
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
                    retval += self.get_child(key).dumps(indentlevel=indentlevel)

                indentlevel -= 1
                if addcomma:
                    retval += "\n"
                    retval += indent * indentlevel
                retval += "}"

                if(self.schemaformat.version == 2 and 
                   'additionalProperties' in data):
                    retval += ", \n"
                    retval += indent * indentlevel
                    retval += '"additionalProperties": '
                    if self.allow_additional_properties():
                        retval += self.get_additional_props_node().dumps(
                                    indentlevel=indentlevel+1)
                    else:
                        retval += 'false'
                    retval += "\n"
                else:
                    retval += "\n"

            elif self.is_type('array'):
                props.remove(self.schemaformat.idmap['items'])
                for prop in props:
                    retval += indent * indentlevel
                    encprop = encoder.encode(prop)
                    val = encoder.encode(data[prop])
                    retval += '%s: %s, \n' % (encprop, val)
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
                    retval += child.dumps(indentlevel=indentlevel)
                retval += "\n"
                indentlevel -= 1
                retval += indent * indentlevel
                retval += "]\n"
            indentlevel -= 1
            retval += indent * indentlevel
            retval += "}"
        else:
            encoder.current_indent_level = indentlevel
            retval = encoder.encode(self.get_data())
        return retval


def generate_schema_data_from_data(jsondata, fmt=schemaformat):
    schema = {}
    properties_id = fmt.idmap['properties']
    items_id = fmt.idmap['items']

    schema['type'] = get_json_type(jsondata, fmt=fmt)

    if schema['type'] == fmt.typemap['object']:
        schema[properties_id] = {}
        for name in jsondata:
            schema[properties_id][name] = \
                generate_schema_data_from_data(jsondata[name], fmt=fmt)
    elif schema['type'] == fmt.typemap['array']:
        schema[items_id] = [generate_schema_data_from_data(jsondata[0], 
                                                           fmt=fmt)]
    return schema


def generate_schema_ordermap(jsondata, jsonordermap=None, fmt=schemaformat):
    ordermap = {}
    properties_id = fmt.idmap['properties']
    items_id = fmt.idmap['items']

    datatype = get_json_type(jsondata, fmt=fmt)
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
                generate_schema_ordermap(jsondata[name], jsonordermap=childmap,
                                         fmt=fmt)
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
            generate_schema_ordermap(jsondata[0], jsonordermap=childmap, 
                                     fmt=fmt)
    return ordermap


def generate_schema_from_data(jsondata, jsonordermap=None, fmt=None,
                             version=schemaformat.version):
    if fmt is None:
        if version == 1:
            fmt = schemaformat_v1
        elif version == 2:
            fmt = schemaformat_v2
        else:
            raise JsonSchemaError("Invalid version")
    schema = generate_schema_data_from_data(jsondata, fmt=fmt)
    ordermap = generate_schema_ordermap(jsondata, jsonordermap=jsonordermap,
                                        fmt=fmt)
    return SchemaNode(data=schema, ordermap=ordermap, fmt=fmt)

