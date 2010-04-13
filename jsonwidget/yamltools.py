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

    if jsonnode.get_depth() > 0 and jsonnode.parent.is_type('array'):
        comment_initial = (indent * (indentlevel - 1)) + "- # "
    else:
        comment_initial = (indent * indentlevel) + "# "
    comment_subsequent = (indent * indentlevel) + "#   "

    retval += jsonnode_get_comment(jsonnode, 
        initial_indent=comment_initial, 
        subsequent_indent=comment_subsequent)

    if jsonnode.get_depth() > 0:
        if jsonnode.parent.is_type('object'):
            retval += indent * indentlevel
            ykey = yaml.safe_dump(jsonnode.get_key())
            enckey = re.sub(r'[\r\n]+\.\.\.[\r\n]+$', '', ykey)
            enckey = re.sub(r'[\r\n]+$', '', enckey)
            retval += enckey
            retval += ": "
            if jsonnode.is_type('object') or jsonnode.is_type('array'):
                retval += "\n"

    if jsonnode.is_type('object') or jsonnode.is_type('array'):
        childkeys = jsonnode.get_child_keys()
        for key in childkeys:
            child = jsonnode.get_child(key)
            retval += jsonnode_to_yaml(child)
    else:
        data = yaml.safe_dump(jsonnode.get_data(), indent=(indentlevel+1)*2)
        retval += re.sub(r'[\r\n]+\.\.\.[\r\n]+$', '\n\n', data)
    
    return retval


