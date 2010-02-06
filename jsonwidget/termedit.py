#!/usr/bin/python
# Library for building urwid-based forms from JSON schemas
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.

from jsonschema import *


class Error(RuntimeError):
    pass

import json
import urwid.curses_display
import urwid
import threading
import sys
import os


from floatedit import FloatEdit


def get_schema_widget(node):
    """
    Class factory for UI widgets.
    node: either a SchemaNode or JsonNode
    returns the appropriate UI widget
    """
    if(isinstance(node, JsonNode)):
        jsonnode = node
    else:
        raise Error("Type error: %s" % type(node).__name__)

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


class ArrayEditWidget(urwid.WidgetWrap):
    """ Map and Seq edit widget and container"""

    def __init__(self, jsonnode):
        self.json = jsonnode
        self.schema = jsonnode.get_schema_node()
        maparray = []
        maparray.append(urwid.Text(self.json.get_title() + ": "))
        leftmargin = urwid.Text("")

        mapfields = self.build_pile()
        self.indentedmap = urwid.Columns([('fixed', 2, leftmargin), mapfields])
        maparray.append(self.indentedmap)
        mappile = urwid.Pile(maparray)
        return urwid.WidgetWrap.__init__(self, mappile)

    def add_node(self, key):
        self.json.add_child(key)
        self.indentedmap.widget_list[1] = self.build_pile()

    def build_pile(self):
        """Build a vertically stacked array of widgets"""
        pilearray = []

        for child in self.json.get_children():
            pilearray.append(get_schema_widget(child))
        pilearray.append(FieldAddButtons(self, self.json))

        return urwid.Pile(pilearray)


class GenericEditWidget(urwid.WidgetWrap):
    """ generic widget used for free text entry (e.g. strings)"""

    def __init__(self, jsonnode):
        self.schema = jsonnode.get_schema_node()
        self.json = jsonnode
        editcaption = urwid.Text(('default', self.json.get_title() + ": "))
        editfield = self.get_edit_field_widget()
        editpair = urwid.Columns([('fixed', 20, editcaption), editfield])
        urwid.WidgetWrap.__init__(self, editpair)

    def get_widget_base_class(self):
        return urwid.Edit

    def store_text_as_data(self, text):
        self.json.set_data(text)

    def get_edit_field_widget(self):
        thiswidget = self

        # CallbackEdit is a closure which effectively gives this object a
        # callback when the text of the widget changes.  This was in lieu of
        # figuring out how to properly use Signals, which may need to wait
        # until I upgrade to using urwid 0.99.

        class CallbackEdit(self.get_widget_base_class()):

            def set_edit_text(self, text):
                urwid.Edit.set_edit_text(self, text)
                thiswidget.store_text_as_data(text)

        innerwidget = CallbackEdit("", str(self.json.get_data()))
        return urwid.AttrWrap(innerwidget, 'editfield', 'editfieldfocus')


class IntEditWidget(GenericEditWidget):
    """ Integer edit widget"""

    def get_widget_base_class(self):
        return urwid.IntEdit

    def store_text_as_data(self, text):
        self.json.set_data(int(text))


class NumberEditWidget(GenericEditWidget):
    """ Number edit widget"""

    def get_widget_base_class(self):
        return FloatEdit

    def store_text_as_data(self, text):
        self.json.set_data(float(text))


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


class FieldAddButtons(urwid.WidgetWrap):
    """ Add a button"""

    def __init__(self, parentwidget, json):
        self.parentwidget = parentwidget
        self.json = json
        caption = urwid.Text(('default', "Add fields: "))
        buttonfield = self.get_buttons()
        editpair = urwid.Columns([('fixed', 20, caption), buttonfield])
        urwid.WidgetWrap.__init__(self, editpair)

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


class JsonWidgetExit(Exception):
    pass


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
        self.yes_no_question("You feel lucky, punk? ")

