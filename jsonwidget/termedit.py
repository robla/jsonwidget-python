#!/usr/bin/python
# Library for building urwid-based forms from JSON schemas.
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.
#
# This file contains all of the glue between the JSON-specific code and the 
# urwid-specific code.


class JsonEditorError(RuntimeError):
    pass


import json
import urwid.curses_display
import urwid
import threading
import sys
import os
import re

from jsonwidget.floatedit import FloatEdit
from jsonwidget.schema import *
from jsonwidget.jsonnode import *
from jsonwidget.pinot import *


def get_schema_widget(node):
    """
    Class factory for UI widgets.
    node: either a SchemaNode or JsonNode
    returns the appropriate UI widget
    """
    if(isinstance(node, JsonNode)):
        jsonnode = node
    else:
        raise JsonEditorError("Type error: %s" % type(node).__name__)

    # we want to make sure that we use a schema-appropriate edit widget, so
    # don't use jsonnode.get_type() directly.
    schemanode = jsonnode.get_schema_node()

    if(schemanode.get_type() == 'map'):
        return ArrayEditWidget(jsonnode)
    elif(schemanode.get_type() == 'seq'):
        return ArrayEditWidget(jsonnode)
    elif(schemanode.get_type() == 'str'):
        if(schemanode.is_enum()):
            return EnumEditWidget(jsonnode)
        else:
            return GenericEditWidget(jsonnode)
    elif(schemanode.get_type() == 'int'):
        return IntEditWidget(jsonnode)
    elif(schemanode.get_type() == 'number'):
        return NumberEditWidget(jsonnode)
    elif(schemanode.get_type() == 'bool'):
        return BoolEditWidget(jsonnode)
    else:
        return GenericEditWidget(jsonnode)

# Series of editing widgets follows, each appropriate to a datatype or two

class BaseJsonEditWidget(urwid.WidgetWrap):
    def init_highlight(self):
        self.set_highlight(self.json.is_selected())

    def set_highlight(self, value=True):
        self.highlighted = value
        
    def is_highlighted(self):
        return self.highlighted
        
    def get_json_node(self):
        return self.json

class ArrayEditWidget(BaseJsonEditWidget):
    """ Map and Seq edit widget and container"""

    def __init__(self, jsonnode):
        self.json = jsonnode
        self.schema = jsonnode.get_schema_node()

        self.init_highlight()

        maparray = []
        maparray.append(urwid.Text(self.json.get_title() + ": "))
        leftmargin = urwid.Text("")

        mapfields = self.build_pile()
        self.indentedmap = urwid.Columns([('fixed', 2, leftmargin), mapfields])
        maparray.append(self.indentedmap)
        mappile = urwid.Pile(maparray)
        return BaseJsonEditWidget.__init__(self, mappile)

    def add_node(self, key):
        self.json.add_child(key)
        self.indentedmap.widget_list[1] = self.build_pile()

    def build_pile(self):
        """Build a vertically stacked array of widgets"""
        pilearray = []

        for child in self.json.get_children():
            childwidget = get_schema_widget(child)
            if(childwidget.is_highlighted()):
                childwidget = urwid.AttrWrap(childwidget, 'selected')
            pilearray.append(childwidget)
        pilearray.append(FieldAddButtons(self, self.json))

        return urwid.Pile(pilearray)



class GenericEditWidget(BaseJsonEditWidget):
    """ generic widget used for free text entry (e.g. strings)"""

    def __init__(self, jsonnode):
        self.schema = jsonnode.get_schema_node()
        self.json = jsonnode
        self.init_highlight()

        if self.is_highlighted():
            style='selected'
        else:
            style='default'
        editcaption = urwid.Text((style, self.json.get_title() + ": "))
        editfield = self.get_edit_field_widget()
        editpair = urwid.Columns([('fixed', 20, editcaption), editfield])
        if self.is_highlighted():
            editpair = urwid.AttrWrap(editpair, 'selected')

        BaseJsonEditWidget.__init__(self, editpair)

    def get_widget_base_class(self):
        return urwid.Edit

    def store_text_as_data(self, text):
        self.json.set_data(text)

    def get_edit_field_widget(self):
        """
        Called on initialization to pull the correct widget and attach a 
        callback linking edits to modification of the corresponding JsonNode.
        """
        thiswidget = self

        # CallbackEdit is a closure which effectively gives this object a
        # callback when the text of the widget changes.  This was in lieu of
        # figuring out how to properly use Signals, which may need to wait
        # until I upgrade to using urwid 0.99.

        class CallbackEdit(self.get_widget_base_class()):

            def set_edit_text(self, text):
                urwid.Edit.set_edit_text(self, text)
                thiswidget.store_text_as_data(text)

        innerwidget = CallbackEdit("", self.get_value_text())
        if self.is_highlighted():
            widget = urwid.AttrWrap(innerwidget, 'selected')
        else:
            widget = urwid.AttrWrap(innerwidget, 'editfield', 'editfieldfocus')
        return widget

    def get_value_text(self):
        return str(self.json.get_data())

class IntEditWidget(GenericEditWidget):
    """ Integer edit widget"""

    def get_widget_base_class(self):
        return urwid.IntEdit

    def store_text_as_data(self, text):
        if text == '':
            self.json.set_data(0)
        else:
            self.json.set_data(int(text))


class NumberEditWidget(GenericEditWidget):
    """ Number edit widget"""

    def get_widget_base_class(self):
        return FloatEdit

    def store_text_as_data(self, text):
        if text == '':
            self.json.set_data(0)
        else:
            self.json.set_data(float(text))

    def get_value_text(self):
        valuetext = str(self.json.get_data())
        return re.sub('.0$', '', valuetext)


class BoolEditWidget(GenericEditWidget):
    """ Boolean edit widget"""

    def get_edit_field_widget(self):
        thiswidget = self

        def on_state_change(self, state, user_data=None):
            thiswidget.json.set_data(state)

        return urwid.CheckBox("", self.json.get_data(),
                              on_state_change=on_state_change)


class EnumEditWidget(GenericEditWidget):
    """ Enumerated string edit widget"""

    def get_edit_field_widget(self):
        options = []
        self.radiolist = []
        thiswidget = self
        for option in self.schema.enum_options():
            if(self.json.get_data() == option):
                state = True
            else:
                state = False

            def on_state_change(self, state, user_data=None):
                if state:
                    thiswidget.json.set_data(user_data)

            options.append(urwid.RadioButton(self.radiolist, option,
                                             state=state, user_data=option,
                                             on_state_change=on_state_change))
        return urwid.GridFlow(options, 13, 3, 1, 'left')


class FieldAddButtons(BaseJsonEditWidget):
    """ Add a button"""

    def __init__(self, parentwidget, json):
        self.parentwidget = parentwidget
        self.json = json
        caption = urwid.Text(('default', "Add fields: "))
        buttonfield = self.get_buttons()
        editpair = urwid.Columns([('fixed', 20, caption), buttonfield])
        BaseJsonEditWidget.__init__(self, editpair)

    def get_buttons(self):
        parentwidget = self.parentwidget
        buttons = []

        def on_press(button, user_data=None):
            parentwidget.add_node(user_data['key'])

        for key in self.json.get_available_keys():
            fieldname = self.json.get_child_title(key)
            buttons.append(urwid.Button(fieldname, on_press, {'key': key}))
        #TODO: remove hard coded widths
        return urwid.GridFlow(buttons, 13, 3, 1, 'left')


class JsonPinotFile(PinotFile):
    '''Glue to underlying JSON object'''

    def __init__(self, jsonfile=None, schemafile=None):
        if jsonfile is None or os.access(jsonfile, os.R_OK):
            # file exists, and we can read it (or we're just passing "None")
            self.json = JsonNode(filename=jsonfile, schemafile=schemafile)
        elif os.access(jsonfile, os.F_OK):
            # file exists, but can't read it
            sys.stderr.write("Cannot access file \"%s\" (check permissions)\n" %
                             jsonfile)
            sys.exit(os.EX_NOINPUT)
        else:
            # must be a new file
            self.json = JsonNode(filename=None, schemafile=schemafile)
            self.set_filename(jsonfile)

    def get_json(self):
        return self.json

    def get_filename(self):
        return self.json.get_filename()

    def save_to_file(self):
        return self.json.save_to_file()

    def set_filename(self, name):
        return self.json.set_filename(name)

    def get_filename_text(self):
        return self.json.get_filename_text()

    def is_saved(self):
        return self.json.is_saved()

    def get_edit_widget(self):
        return get_schema_widget(self.json)

    def get_walker(self):
        widget = self.get_edit_widget()
        return JsonWalker([widget])

class JsonWalker(urwid.SimpleListWalker):
    def get_deepest_focus_widget_with_json(self):
        """
        Get the innermost widget with a JsonNode corresponding to where the 
        cursor is right now. 
        """
        focuswidget = self.get_focus()[0]
        deeperwidget = focuswidget
        # Walk down the widget tree calling get_focus until we 
        # can't call it anymore.
        while deeperwidget is not None:
            # Call get_json_node on the way down because the bottommost node 
            # may not have an associated JsonNode.
            if hasattr(deeperwidget, 'get_json_node'):
                focuswidget = deeperwidget
            deeperwidget = self._get_deeper_focus_widget(deeperwidget)
        return focuswidget

    def _get_deeper_focus_widget(self, focuswidget):
        """ Recursion helper for get_deepest_focus_node """
        
        if hasattr(focuswidget, 'get_w'):
            return focuswidget.get_w()
        if hasattr(focuswidget, 'get_focus'):
            return focuswidget.get_focus()
        else:
            return None

    def set_tree_focus(self):
        """
        Get the innermost widget with a JsonNode corresponding to where the 
        cursor is right now. 
        """
        focuswidget = self.get_focus()[0]
        deeperwidget = focuswidget
        self.focusresetlist = []
        # Walk down the widget tree calling get_focus until we 
        # can't call it anymore.
        while deeperwidget is not None:
            # Call get_json_node on the way down because the bottommost node 
            # may not have an associated JsonNode.
            if hasattr(deeperwidget, 'get_json_node'):
                focuswidget = deeperwidget
            deeperwidget = self._get_deeper_focus_widget(deeperwidget)
        return focuswidget

    def _set_deeper_tree_focus(self, focuswidget):
        """ Recursion helper for get_deepest_focus_node """
        
        if hasattr(focuswidget, 'get_w'):
            return focuswidget.get_w()
        if hasattr(focuswidget, 'get_focus'):
            return focuswidget.get_focus()
        else:
            return None
        

class JsonEditor(PinotFileEditor):
    """
    JSON editor specific commands
    These routines deal with the specifics of a JSON editor.
    """
    def __init__(self, jsonfile=None, schemafile=None, 
                 program_name="JsonWidget"):
        self.file = JsonPinotFile(jsonfile=jsonfile, schemafile=schemafile)
        self.json = self.file.get_json()
        self.schema = self.json.get_schema_node()
        return PinotFileEditor.__init__(self, program_name=program_name)

    def handle_delete_node_request(self):
        """Handle ctrl d - "delete node"."""
        focuswidget = self.walker.get_deepest_focus_widget_with_json()
        focusnode = focuswidget.get_json_node()
        focusnode.set_cursor(focusnode)
        self.set_body()
        self.yes_no_question("You feel lucky, punk? ",
                             yesfunc=self.cleanup_delete_request,
                             nofunc=self.cleanup_delete_request,
                             cancelfunc=self.cleanup_delete_request)

    def cleanup_delete_request(self):
        self.json.set_cursor(None)
        self.set_body()
        self.cleanup_user_question()
            

