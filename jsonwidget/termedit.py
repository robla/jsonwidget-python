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
from jsonwidget.treetools import *



# Series of editing widgets follows, each appropriate to a datatype or two

class BaseJsonEditWidget(TreeWidget):
    def __init__(self, parent, key, value):
        TreeWidget.__init__(self, parent, key, value)

    def init_highlight(self):
        self.set_highlight(self.json.is_selected())

    def set_highlight(self, value=True):
        self.highlighted = value
        
    def is_highlighted(self):
        return self.highlighted
        
    def get_json_node(self):
        return self.json

class ArrayEditWidget(ParentWidget):
    """ Map and Seq edit widget and container"""

    def __init__(self, parent, key, value):
        self.json = value
        self.schema = value.get_schema_node()
        self.__super.__init__(parent, key, value)
        
    def get_display_text(self):
        return self.json.get_title() + ": "

    def self_as_parent(self):
        """Return self as a parent object."""
        return self.get_parent().get_subtree(self.get_key())

    def get_json_node(self):
        return self.json


class GenericEditWidget(BaseJsonEditWidget):
    """ generic widget used for free text entry (e.g. strings)"""

    def __init__(self, parent, key, jsonnode):
        self.schema = jsonnode.get_schema_node()
        self.json = jsonnode
        self.init_highlight()
        self.__super.__init__(parent, key, jsonnode)

    def get_widget(self):
        if self.is_highlighted():
            style='selected'
        else:
            style='default'
        editcaption = urwid.Text((style, self.json.get_title() + ": "))
        editfield = self.get_edit_field_widget()
        editpair = urwid.Columns([('fixed', 20, editcaption), editfield])
        if self.is_highlighted():
            editpair = urwid.AttrWrap(editpair, 'selected')

        self._innerwidget = editpair
        return self._innerwidget

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

    def keypress(self, size, key):
        """Pass keystrokes through to child widget"""
        return self.get_w().keypress(size, key)


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


class JsonWidgetParent(ParentNode):
    def __init__(self, jsonobj, parent=None, key=None):
        self.json = jsonobj
        if not isinstance(self.json, JsonNode):
            raise RuntimeError(str(self.json))

        super(self.__class__, self).__init__(jsonobj, 
                                             parent=parent,
                                             key=self.json.get_key())

    def get_items(self):
        return self.json.get_child_keys()

    def get_child_value(self, key):
        if key is None:
            return self.json
        else:
            return self.json.get_child(key)

    def get_widget_constructor_for_value(self, value):
        # we want to make sure that we use a schema-appropriate edit widget, so
        # don't use value.get_type() directly.
        schemanode = value.get_schema_node()

        if(schemanode.get_type() == 'map'):
            return ArrayEditWidget
        elif(schemanode.get_type() == 'seq'):
            return ArrayEditWidget
        elif(schemanode.get_type() == 'str'):
            if(schemanode.is_enum()):
                return EnumEditWidget
            else:
                return GenericEditWidget
        elif(schemanode.get_type() == 'int'):
            return IntEditWidget
        elif(schemanode.get_type() == 'number'):
            return NumberEditWidget
        elif(schemanode.get_type() == 'bool'):
            return BoolEditWidget
        else:
            return GenericEditWidget

    def get_widget_constructor_for_child(self, key):
        jsonnode = self.get_child_value(key)
        return self.get_widget_constructor_for_value(jsonnode)

class JsonWalker(TreeWalker):
    pass


class JsonFrame(urwid.ListBox):
    def __init__(self, jsonobj):
        self.json = jsonobj
        walker = JsonWalker(JsonWidgetParent(self.json))
        return super(self.__class__, self).__init__(walker)


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
        self.listbox = JsonFrame(self.json)
        return PinotFileEditor.__init__(self, program_name=program_name)

    def handle_delete_node_request(self):
        """Handle ctrl d - "delete node"."""
        focuswidget = self.walker.get_deepest_focus_widget_with_json()
        focusnode = focuswidget.get_json_node()
        focusnode.set_cursor(focusnode)
        self.set_body()
        self.yes_no_question("Delete selected field? ",
                             yesfunc=self.handle_delete_node(focuswidget),
                             nofunc=self.cleanup_delete_request,
                             cancelfunc=self.cleanup_delete_request)

    def handle_delete_node(focuswidget):
        self.cleanup_delete_request()        

    def cleanup_delete_request(self):
        self.json.set_cursor(None)
        self.set_body()
        self.cleanup_user_question()

    def get_edit_widget(self):
        return get_schema_widget(self.json)

    def get_walker(self):
        widget = self.get_edit_widget()
        return JsonWalker([widget])

