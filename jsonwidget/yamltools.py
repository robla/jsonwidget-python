#!/usr/bin/python
# Tools for importing/exporting jsonwidget objects as YAML
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.

import textwrap
import yaml
import re
import copy
            
def jsonnode_get_comment(jsonnode, initial_indent='# ', 
                         subsequent_indent='#    '):
    """return a comment used in YAML source or other possible sources"""

    comment = jsonnode.get_title()
    comment += ": "
    comment += jsonnode.get_description()
    if jsonnode.is_enum():
        comment += ' Choices: "'
        comment += '", "'.join(jsonnode.enum_options())
        comment += '"'
    comment += "\n"
    retval = "\n".join(textwrap.wrap(comment, initial_indent=initial_indent,
                        subsequent_indent=subsequent_indent))
    return retval + "\n"


def jsonnode_to_yaml(jsonnode, indentlevel=None, firstindent=True):
    """ 
    Return the object as a YAML string, with comments pulled from the 
    schema
    """

    retval = ""
    indent = " " * 2
    if indentlevel is None:
        indentlevel = jsonnode.get_depth()

    if jsonnode.is_type('object'):
        childkeys = jsonnode.get_child_keys()
        firstkey = True
        for key in childkeys:
            child = jsonnode.get_child(key)
            if firstindent or not firstkey:
                #retval += indent * indentlevel
                comment_initial = (indent * indentlevel) + "# "
                comment_subsequent = (indent * indentlevel) + "#   "
            else:
                comment_initial = "# "
                comment_subsequent = (indent * indentlevel) + "#   "
            retval += jsonnode_get_comment(child, 
                initial_indent=comment_initial, 
                subsequent_indent=comment_subsequent)
            retval += indent * indentlevel
            firstkey = False
            retval += yaml.safe_dump(key)[:-5]
            retval += ": "
            if child.is_type('object') or child.is_type('array'):
                retval += "\n"
                retval += indent * indentlevel
                retval += jsonnode_to_yaml(child)
            else:
                retval += jsonnode_to_yaml(child, firstindent=False)
    elif jsonnode.is_type('array'):
        def render_array_item(item, firstindent=indentlevel):
            array_yaml = indent * firstindent
            comment_initial = "# "
            comment_subsequent = (indent * indentlevel) + "#   "
            array_yaml += jsonnode_get_comment(item, 
                initial_indent=comment_initial, 
                subsequent_indent=comment_subsequent)

            array_yaml += indent * indentlevel
            array_yaml += "- "
            array_yaml += jsonnode_to_yaml(item, firstindent=False)
            return array_yaml

        childkeys = copy.copy(jsonnode.get_child_keys())
        if firstindent:
            child = jsonnode.get_child(childkeys.pop(0))
            retval += render_array_item(child, firstindent=indentlevel-1)
        for key in childkeys:
            child = jsonnode.get_child(key)
            retval += render_array_item(child)

    else:
        if firstindent:
            retval += indent * indentlevel
        data = yaml.safe_dump(jsonnode.get_data())
        retval += re.sub(r'[\r\n]+\.\.\.[\r\n]+$', '\n\n', data)
    return retval


