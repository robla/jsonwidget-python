#!/usr/bin/python
# Library for reading JSON files according to given JSON Schema
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.

import json
import uuid
import base64

from jsonwidget.schema import *
from jsonwidget.jsonbase import *
from jsonwidget.jsontypes import get_json_type

class JsonNodeError(RuntimeError):
    pass


class JsonNode(JsonBaseNode):
    """
    JsonNode is a class to store the data associated with a schema.  Each node
    of the tree gets tied to a SchemaNode.
    """

    def __init__(self, key=None, parent=None, filename=None, data=None,
                 schemanode=None, schemadata=None, schemafile=None, 
                 ordermap=None):
        self.filename = filename
        if self.filename is not None:
            if data is None:
                try:
                    self.load_from_file()
                except ValueError as inst:
                    raise JsonNodeError("Error in %s: %s" % (self.filename, 
                                                            inst))
        else:
            self.data = data

        if schemanode is None:
            schemanode = SchemaNode(key=key, data=schemadata,
                                    filename=schemafile)

        self.schemanode = schemanode

        if ordermap is not None:
            self.ordermap = ordermap

        # local index for the node
        self.key = key
        # object ref for the parent
        self.parent = parent
        # self.children will get set in attach_schema_node if there are any
        self.children = []


        if self.parent is None:
            self.depth = 0
            self.root = self
            # edit counter to help figure out if the data is out of line with
            # what is on disk
            self.editcount = 0
            self.savededitcount = 0
            self.cursor = None
        else:
            self.depth = self.parent.get_depth() + 1
            self.root = self.parent.get_root()

        if schemanode.is_type('idref'):
            schemanode = schemanode.resolve_fragment_id()

        if not self.is_type_match(schemanode):
            idstring = self.get_id_string()
            filename = self.get_filename()
            jsontype = self.get_type()
            schematype = schemanode.get_type()
            schemaname = schemanode.get_filename()
            raise JsonNodeError(
                ("Type mismatch in %s%s - jsontype: %s schematype: %s\n" +
                 "Schema: %s\nTry using a different schema") %
                (filename, idstring, jsontype, schematype, schemaname))
        else:
            self.attach_schema_node(schemanode)
        if self.depth == 0:
            self.set_saved(True)

    def get_root(self):
        return self.root

    def save_to_file(self, filename=None):
        if filename is not None:
            self.filename = filename
        if self.filename is None:
            import tempfile
            fd = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
            self.filename = fd.name
        else:
            fd = open(self.filename, 'w+')
        json.dump(self.get_data(), fd, indent=4, sort_keys=True)
        self.savededitcount = self.editcount

    def is_type_match(self, schemanode):
        # is the json type appropriate for the expected schema type?
        is_type_match = (schemanode.is_type('any') or
                         self.get_type() == schemanode.get_type() or
                         self.is_type('null') or
                         (self.is_type('integer') and 
                          schemanode.is_type('number')))

        return is_type_match

    def attach_schema_node(self, schemanode):
        '''Pair this data node to the corresponding part of the schema'''
        self.schemanode = schemanode

        def init_object():
            self.children = {}
            if self.is_type('null'):
                self.set_data({})
                self.set_type('object')
        if schemanode.is_type('object'):
            init_object()
        elif schemanode.is_type('array'):
            self.children = []
        if self.schemanode.is_type('any') and self.is_type('object'):
            init_object()
            for subkey, subdata in self.data.items():
                self.children[subkey] = JsonNode(key=subkey, data=subdata,
                    parent=self, schemanode=self.schemanode)
        elif self.schemanode.is_type('any') and self.is_type('array'):
            self.children = []
            i = 0
            for subdata in self.data:
                self.children.append(JsonNode(key=i, data=subdata, parent=self,
                    schemanode=self.schemanode))
                i += 1
        elif self.is_type('object'):
            schemakeys = self.schemanode.get_child_keys()
            # first add all nodes for which there is JSON data, removing them
            # from our local schemakeys array so that we can iterate through 
            # the schema keys we miss in this pass
            for subkey, subdata in self.data.items():
                try:
                    subschemanode = self.schemanode.get_child(subkey)
                except KeyError:
                    if self.schemanode.allow_additional_properties():
                        subschemanode = self.schemanode.get_additional_props_node()
                    else:
                        idstring = self.get_id_string()
                        validkeys = self.schemanode.get_child_keys()
                        validkeystring = ", ".join(validkeys)
                        filename = self.get_filename()
                        raise JsonNodeError(
                            "Invalid key: \"%s\" in %s%s.  Valid keys: %s" % 
                            (subkey, filename, idstring, validkeystring))
                if subschemanode is None:
                    raise JsonNodeError(
                        "Validation error: %s not a valid key in %s" %
                        (subkey, self.schemanode.get_key()))
                if subkey in schemakeys:
                    schemakeys.remove(subkey)
                elif not self.schemanode.allow_additional_properties():
                    raise JsonNodeError(
                        "Invalid key: \"%s\" in %s%s.  Valid keys: %s" % 
                        (subkey, filename, idstring, validkeystring))
                try:
                    ordermap = self.ordermap['children'][subkey]
                except AttributeError:
                    ordermap = None
                self.children[subkey] = JsonNode(key=subkey, data=subdata,
                    parent=self, schemanode=subschemanode, 
                    ordermap=ordermap)
              
            # iterate through the unpopulated schema keys and add subnodes if 
            # the nodes are required
            for subkey in schemakeys:
                subschemanode = self.schemanode.get_child(subkey)
                if subschemanode.is_required():
                    self.add_child(subkey)
        elif self.is_type('array'):
            i = 0
            for subdata in self.data:
                subschemanode = self.schemanode.get_child(i)
                try:
                    ordermap = self.ordermap['children'][i]
                except AttributeError:
                    ordermap = None
                self.children.append(JsonNode(key=i, data=subdata, parent=self,
                    schemanode=subschemanode, ordermap=ordermap))
                i += 1
            if i == 0 and self.schemanode.get_child(0).is_required():
                self.add_child(0)

    def get_schema_node(self):
        return self.schemanode

    def get_type(self):
        """Get type string as defined by the schema language"""
        return get_json_type(self.data, fmt=self.schemanode.get_format())

    def is_type(self, cmptype):
        fmt = self.schemanode.get_format()
        return fmt.typemap_rev[self.get_type()] == cmptype

    def get_key(self):
        return self.key

    def set_key(self, key):
        self.key = key

    def set_data(self, data):
        """Set raw data"""

        # TODO: move to storing child data exclusively in children, because
        # current method has n log n memory footprint.

        if not self.data == data:
            self.root.editcount += 1
        self.data = data
        if(self.depth > 0):
            self.parent.set_child_data(self.key, data)

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
            raise JsonNodeError("self.children has invalid type %s" %
                                type(self.children).__name__)

    def get_child(self, key):
        return self.children[key]

    def _get_key_order(self):
        ordermap = self.schemanode._get_key_order()
        return ordermap

    def get_available_keys(self):
        """
        This function returns the list of keys that don't yet have associated
        json child nodes associated with them.
        """
        typemap = self.schemanode

        if(self.schemanode.is_type('object')):
            schemakeys = set(self.schemanode.get_child_keys())
            jsonkeys = set(self.get_child_keys())
            unusedkeys = schemakeys.difference(jsonkeys)
            if (self.schemanode.schemaformat.version == 1 and
                self.schemanode.allow_additional_properties()):
                # remove the additional props key if there is one
                propkey = self.schemanode.get_additional_props_node().get_key()
                try:
                    unusedkeys.remove(propkey)
                except:
                    pass
            if self.schemanode.allow_additional_properties():
                nextkey = \
                    base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip('=')
                unusedkeys.add(nextkey)
            sortedkeys = self.sort_keys(list(unusedkeys))
            return sortedkeys
        elif(self.schemanode.is_type('array')):
            return [len(self.children)]
        else:
            raise JsonNodeError("type %s not implemented" % self.get_type())

    def set_child_data(self, key, data):
        if(self.data is None):
            type = self.schemanode.get_type()
            self.data = self.schemanode.get_blank_value()
            self.root.editcount += 1
        if(self.is_type('array') and key == len(self.data)):
            self.data.append(data)
            self.root.editcount += 1
        else:
            if not key in self.data or not self.data[key] == data:
                self.root.editcount += 1
            self.data[key] = data

    def is_saved(self):
        return self.savededitcount == self.editcount

    def set_saved(self, saved=True):
        if(saved):
            self.editcount = 0
        else:
            self.editcount = 1
        self.savededitcount = 0

    def add_child(self, key=None):
        schemanode = self.schemanode.get_child(key)
        newnode = JsonNode(key=key, data=schemanode.get_blank_value(),
                           parent=self, schemanode=schemanode)
        self.set_child_data(key, newnode.get_data())
        if(self.is_type('array')):
            self.children.insert(key, newnode)
        else:
            self.children[key] = newnode

    def delete_child(self, key=None):
        self.root.editcount += 1
        self.data.pop(key)
        self.children.pop(key)

        # since children keep track of their own keys, we have to refresh
        # them
        if(self.is_type('array')):
            for i in range(len(self.children)):
                self.children[i].set_key(i)

        # propogate the change up the tree
        if(self.depth > 0):
            self.parent.set_child_data(self.key, self.data)

    def is_enum(self):
        return self.schemanode.is_enum()

    def enum_options(self):
        return self.schemanode.enum_options()

    def get_depth(self):
        """How deep is this node in the tree?"""
        return self.depth

    def print_tree(self):
        """Debugging function"""
        if (self.is_type('object') or self.is_type('array')):
            print self.schemanode.get_title()
            for child in self.get_children():
                child.print_tree()
        else:
            print self.schemanode.get_title() + ": " + self.get_data()

    def get_title(self):
        schematitle = self.schemanode.get_title()
        if(self.depth > 0 and self.parent.schemanode.is_type('array')):
            title = "%s #%i" % (schematitle, self.get_key() + 1)
        else:
            title = schematitle
        return title


    def get_description(self):
        return self.schemanode.get_description()

    def get_child_title(self, key):
        childschema = self.schemanode.get_child(key)
        schematitle = childschema.get_title()
        if(self.schemanode.is_type('array')):
            title = "%s #%i" % (schematitle, key + 1)
        else:
            title = schematitle
        return title

    def is_root(self):
        return self.parent is None

    def set_cursor(self, node):
        self.root.cursor = node

    def get_cursor(self):
        return self.root.cursor

    def is_selected(self):
        if self.root.cursor is None:
            return False
        elif self.root.cursor == self:
            return True
        elif self.is_root():
            return False
        else:
            return self.parent.is_selected()
            
    def is_deletable(self):
        parent = self.parent
        if parent is not None and parent.is_type('array'):
            if len(parent.get_children()) > 1:
                return True
            else:
                return not self.schemanode.is_required()
        else:
            return not self.schemanode.is_required()

    def get_id_string(self):
        idchain = []
        node = self
        while node.get_key() is not None:
            idchain.insert(0, str(node.get_key()))
            node = node.parent
        return "[" + "][".join(idchain) + "]"
        
    def is_additional_props_node(self):
        return self.schemanode.is_additional_props_node()

    def change_key(self, key):
        self.get_parent().change_child_key(self.get_key(), key)

    def change_child_key(self, oldkey, newkey):
        schemakeys = self.schemanode.get_child_keys()
        if newkey in self.children or newkey in schemakeys:
            raise JsonNodeError("%s is already in use" % newkey)
        if oldkey != newkey:
            self.root.editcount += 1
            node = self.children.pop(oldkey)
            self.children[newkey] = node
            node.set_key(newkey)
            data = self.data.pop(oldkey)
            self.data[newkey] = data

