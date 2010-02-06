#!/usr/bin/python
# Library for reading JSON files according to given JSON Schema
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.

import json


class Error(RuntimeError):
    pass


class JsonBaseNode:
    """ abstract base class for SchemaNode and JsonNode """
    # TODO: pull more functions in from subclasses

    def get_filename(self):
        return self.filename

    def get_filename_text(self):
        if self.filename is None:
            return "(new file)"
        else:
            return self.filename

    def set_filename(self, filename):
        self.filename = filename
        self.savededitcount = 0


