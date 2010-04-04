#!/usr/bin/python
# Library for reading JSON files according to given JSON Schema
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.

import json

from jsonwidget.jsonorder import *


class JsonBaseError(RuntimeError):
    pass


class JsonBaseNode:
    """ abstract base class for SchemaNode and JsonNode """
    # TODO: pull more functions in from subclasses

    def get_filename(self):
        if self.parent is None:
            return self.filename
        else:
            return self.parent.get_filename()

    def get_filename_text(self):
        filename = self.get_filename()
        if filename is None:
            return "(new file)"
        else:
            return self.filename

    def set_filename(self, filename):
        self.filename = filename
        self.savededitcount = 0

    def load_from_file(self, filename=None):
        if filename is not None:
            self.filename = file
        with open(self.filename, 'r') as f:
            jsonbuffer = f.read()
        f.closed  
        self.data = json.loads(jsonbuffer)
        self.ordermap = JsonOrderMap(jsonbuffer).get_order_map()

    def _get_key_order(self):
        """virtual function"""
        pass

    def sort_keys(self, keys):
        ordermap = self._get_key_order()
        def keycmp(a, b):
            try:
                ai = ordermap.index(a)
            except:
                ai = len(keys)
            try:
                bi = ordermap.index(b)
            except:
                bi = len(keys)
            if ai == bi == len(keys):
                return cmp(a, b)
            else:
                return cmp(ai, bi)
        return sorted(keys, cmp=keycmp)

    def get_child_keys(self):
        if isinstance(self.children, dict):
            keys = self.children.keys()
            return self.sort_keys(keys)
        elif isinstance(self.children, list):
            return range(len(self.children))
        else:
            raise JsonBaseError("self.children has invalid type %s" %
                                type(self.children).__name__)

    def get_data(self):
        return self.data


        
