#!/usr/bin/python
# Widgets for building urwid-based forms from JSON schemas.
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.
#
# This file contains the widgets which interface both with the JSON-specific
# code and the urwid-specific code.


class JsonEditorError(RuntimeError):
    pass


import threading
import sys
import os
import re
import json

import urwid.curses_display
import urwid

from jsonwidget.floatedit import FloatEdit
from jsonwidget.schema import *
from jsonwidget.jsonnode import *
from jsonwidget.pinot import *
from jsonwidget.treetools import *

# Series of editing widgets follows, each appropriate to a datatype or two

class BaseJsonEditWidget(TreeWidget):
    def get_json_node(self):
        return self.get_node().get_value()

    def unhandled_keys(self, size, key):
        """Overriding default selection behavior"""
        return key

class ArrayEditWidget(ParentWidget):
    """ Map and Seq edit widget and container"""
    def get_json_node(self):
        return self.get_node().get_value()

    def get_display_text(self):
        jsonnode = self.get_json_node()
        title = jsonnode.get_title()
        if jsonnode.is_additional_props_node():
            title = "%s (%s)" % (title, jsonnode.get_key())
        return title + ": "

    def unhandled_keys(self, size, key):
        """Overriding default selection behavior"""
        return key


class GenericEditWidget(BaseJsonEditWidget):
    """ generic widget used for free text entry (e.g. strings)"""
    def load_inner_widget(self):
        jsonnode = self.get_json_node()
        editcaption = urwid.Text(jsonnode.get_title() + ": ")
        editfield = self.get_edit_field_widget()
        parentnode = self.get_node().get_parent()
        captionmax = max(parentnode.get_title_max_length() + 4, 10)
        editpair = urwid.Columns([('fixed', captionmax, editcaption), 
                                 editfield])
        if self.is_selected():
            editpair = urwid.AttrWrap(editpair, 'selected', 
                                      focus_attr='selected focus')
        else:
            editpair = urwid.AttrWrap(editpair, 'body', 
                                      focus_attr='focus')

        return editpair

    def get_widget_base_class(self):
        return urwid.Edit

    def store_text_as_data(self, text):
        self.get_json_node().set_data(text)

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
        if self.is_selected():
            widget = urwid.AttrWrap(innerwidget, 'selected')
        else:
            widget = urwid.AttrWrap(innerwidget, 'editfield', 'editfieldfocus')
        return widget

    def get_value_text(self):
        value = self.get_json_node().get_data()
        if isinstance(value, basestring):
            return value
        else:
            return str(value)

    def keypress(self, size, key):
        """Pass keystrokes through to child widget"""
        return self.get_w().keypress(size, key)


class IntEditWidget(GenericEditWidget):
    """ Integer edit widget"""

    def get_widget_base_class(self):
        return urwid.IntEdit

    def store_text_as_data(self, text):
        jsonnode = self.get_json_node()
        if text == '':
            jsonnode.set_data(0)
        else:
            jsonnode.set_data(int(text))


class NumberEditWidget(GenericEditWidget):
    """ Number edit widget"""

    def get_widget_base_class(self):
        return FloatEdit

    def store_text_as_data(self, text):
        jsonnode = self.get_json_node()
        if text == '':
            jsonnode.set_data(0)
        else:
            jsonnode.set_data(float(text))

    def get_value_text(self):
        jsonnode = self.get_json_node()
        valuetext = str(jsonnode.get_data())
        return re.sub('.0$', '', valuetext)


class BoolEditWidget(GenericEditWidget):
    """ Boolean edit widget"""

    def get_edit_field_widget(self):
        jsonnode = self.get_json_node()

        def on_state_change(self, state, user_data=None):
            jsonnode.set_data(state)

        return urwid.CheckBox("", jsonnode.get_data(),
                              on_state_change=on_state_change)


class EnumEditWidget(GenericEditWidget):
    """ Enumerated string edit widget"""

    def get_edit_field_widget(self):
        options = []
        self._radiolist = []
        jsonnode = self.get_json_node()
        schemanode = jsonnode.get_schema_node()
        maxlen = 3
        for option in schemanode.enum_options():
            if(jsonnode.get_data() == option):
                state = True
            else:
                state = False

            def on_state_change(self, state, user_data=None):
                if state:
                    jsonnode.set_data(user_data)

            maxlen = max(len(option), maxlen)
            options.append(urwid.RadioButton(self._radiolist, option,
                                             state=state, user_data=option,
                                             on_state_change=on_state_change))
        return urwid.GridFlow(options, maxlen+6, 2, 0, 'left')


class KeyEditWidget(GenericEditWidget):
    """ Edit the key associated with this node """

    def load_inner_widget(self):
        editcaption = urwid.Text("(key) -> ")
        self._editfield = self.get_edit_field_widget()
        editpair = urwid.Columns([('fixed', 9, editcaption), self._editfield])
        if self.is_selected():
            editpair = urwid.AttrWrap(editpair, 'selected', 
                                      focus_attr='selected focus')
        else:
            editpair = urwid.AttrWrap(editpair, 'body', 
                                      focus_attr='focus')
        return editpair

    def store_text_as_data(self, text):
        """Change the key for the node"""
        treenode = self.get_node().get_parent()
        key = treenode.get_key()
        if text != key:
            try:
                treenode.change_key(text)
            except TreeWidgetError as inst:
                # probably a duplicate key
                self.set_edit_text(key)
                raise PinotAlert(str(inst))
        # update the key text in the parent widget
        parentwidget = treenode.get_widget()
        parentwidget.update_widget()

    def get_value_text(self):
        return self.get_node().get_parent().get_value().get_key()

    def set_edit_text(self, text):
        """Set the text in the editing field."""
        return self._editfield.set_edit_text(text)


class KeyEditKey(object):
    """
    Dummy class used as a key for KeyEditWidget.  This library uses an object
    instance rather than a string as a key to prevent collisions with valid 
    JSON keys.
    """
    pass


class KeyEditNode(TreeNode):
    def __init__(self, jsonnode, parent=None, key=None, depth=None):
        TreeNode.__init__(self, jsonnode, key=key, parent=parent, depth=depth)        

    def load_widget(self):
        return KeyEditWidget(self)

    def is_deletable(self):
        return False

    def is_insertable(self):
        """ Can a node be inserted at this point in the tree? """
        return self.get_value().is_insertable()


class FieldAddButtons(BaseJsonEditWidget):
    """ Add a button"""

    def load_inner_widget(self):
        jsonnode = self.get_node().get_parent().get_value()

        if jsonnode.get_schema_node().is_type('array'):
            caption = urwid.Text("Add item: ")
        else:
            caption = urwid.Text("Add field(s): ")
        buttonfield = self.get_buttons()
        editpair = urwid.Columns([('fixed', 20, caption), buttonfield])
        return editpair

    def get_buttons(self):
        buttons = []
        parentnode = self.get_node().get_parent()

        def on_press(button, user_data=None):
            parentnode.add_child_node(user_data['key'])

        jsonnode = self.get_node().get_parent().get_value()
        maxlen = 3
        for key in jsonnode.get_available_keys():
            fieldname = jsonnode.get_child_title(key)
            maxlen = max(len(fieldname), maxlen)
            buttons.append(urwid.Button(fieldname, on_press, {'key': key}))
        return urwid.GridFlow(buttons, maxlen+4, 2, 0, 'left')

class FieldAddKey(object):
    """
    Dummy class used as a key for FieldAddButtons.  This library uses an object
    instance rather than a string as a key to prevent collisions with valid 
    JSON keys.
    """
    pass


class FieldAddNode(TreeNode):
    def __init__(self, jsonnode, parent=None, key=None, depth=None):
        TreeNode.__init__(self, jsonnode, key=key, parent=parent, depth=depth)        
        
    def load_widget(self):
        return FieldAddButtons(self)

    def is_deletable(self):
        return False
        
    def is_insertable(self):
        """ Can a node be inserted at this point in the tree? """
        return self.get_value().is_insertable()


class JsonWidgetNode(TreeNode):
    def __init__(self, jsonnode, parent=None, key=None, depth=None):
        key = jsonnode.get_key()
        depth = jsonnode.get_depth()
        TreeNode.__init__(self, jsonnode, key=key, parent=parent, depth=depth)

    def load_widget(self):
        jsonnode = self.get_value()
        # we want to make sure that we use a schema-appropriate edit widget, so
        # don't use jsonnode.get_type() directly.
        schemanode = jsonnode.get_schema_node()

        if(schemanode.is_type('string')):
            if(schemanode.is_enum()):
                return EnumEditWidget(self)
            else:
                return GenericEditWidget(self)
        elif(schemanode.is_type('integer')):
            return IntEditWidget(self)
        elif(schemanode.is_type('number')):
            return NumberEditWidget(self)
        elif(schemanode.is_type('boolean')):
            return BoolEditWidget(self)
        else:
            return GenericEditWidget(self)

    def delete_node(self):
        parent = self.get_parent()
        if parent is None:
            jsonnode = self.get_value()
            jsonnode.set_data(None)
            self.get_widget(reload=True)
        else:
            parent.delete_child_node(self.get_key())
            
    def is_deletable(self):
        return self.get_value().is_deletable()

    def insert_node(self):
        """ Insert a node before this one """
        parent = self.get_parent()
        parent.insert_child_node(self.get_key())

    def is_insertable(self):
        """ Can a node be inserted at this point in the tree? """
        return self.get_value().is_insertable()

class JsonWidgetParent(ParentNode):
    def __init__(self, jsonnode, parent=None, key=None, depth=None, 
                 listbox=None):
        key = jsonnode.get_key()
        depth = jsonnode.get_depth()
        self._fieldaddkey = FieldAddKey()
        if jsonnode.is_additional_props_node():
            self._keyeditkey = KeyEditKey()
        self._listbox = listbox
        ParentNode.__init__(self, jsonnode, key=key, parent=parent, 
                            depth=depth)

    def load_widget(self):
        return ArrayEditWidget(self)

    def load_child_keys(self):
        jsonnode = self.get_value()
        keys = []
        if jsonnode.is_additional_props_node():
            keys.append(self._keyeditkey)
        keys.extend(jsonnode.get_child_keys())
        if len(jsonnode.get_available_keys()) > 0:
            fieldaddkey = self._fieldaddkey
            keys.append(fieldaddkey)
        return keys

    def load_child_node(self, key):
        depth = self.get_depth() + 1
        if isinstance(key, FieldAddKey):
            return FieldAddNode(None, parent=self, depth=depth, key=key)
        elif isinstance(key, KeyEditKey):
            return KeyEditNode(None, parent=self, depth=depth, key=key)
        else:
            jsonnode = self.get_value().get_child(key)
            schemanode = jsonnode.get_schema_node()
            if schemanode.is_type('object') or schemanode.is_type('array'):
                return JsonWidgetParent(jsonnode, parent=self, key=key, 
                                        depth=depth, listbox=self._listbox)
            else:
                return JsonWidgetNode(jsonnode, parent=self, key=key, 
                                      depth=depth)

    def add_child_node(self, key):
        # update the json first
        jsonnode = self.get_value()
        jsonnode.add_child(key)
        # refresh the child key cache
        self.get_child_keys(reload=True)
        newnode = self.get_child_node(key)
        # change the focus to the new field.  This will be especially
        # important should this be the last new field, since the last button
        # in the row we're currently focused on will disappear.
        size = self._listbox._size
        offset, inset = self._listbox.get_focus_offset_inset(size)
        self._listbox.change_focus(size, newnode, coming_from='below',
                                   offset_inset = offset)
        # refresh the field add buttons, since the list of available keys has
        # changed
        if len(jsonnode.get_available_keys()) > 0:
            fieldaddnode = self.get_child_node(self._fieldaddkey)
            fieldaddnode.get_widget(reload=True)

    def delete_node(self):
        '''Delete this node and all of its children'''
        parent = self.get_parent()
        if parent is None:
            jsonnode = self.get_value()
            keys = jsonnode.get_child_keys()
            for key in reversed(keys):
                jsonnode.delete_child(key)
                self._children.pop(key)
            jsonnode.set_data(None)
            self.get_child_keys(reload=True)
            self.get_widget(reload=True)
            # refresh the field add buttons, since the list of available keys 
            # has changed
            fieldaddnode = self.get_child_node(self._fieldaddkey)
            fieldaddnode.get_widget(reload=True)
        else:
            parent.delete_child_node(self.get_key())

    def delete_child_node(self, key):
        # get ready to focus on previous node
        childnode = self.get_child_node(key)
        prevnode = childnode.get_widget().prev_inorder().get_node()
        size = self._listbox._size
        offset, inset = self._listbox.get_focus_offset_inset(size)
        # update the json
        jsonnode = self.get_value()
        jsonnode.delete_child(key)
        # update this node tree
        self._children.pop(key)
        # change focus
        keys = self.get_child_keys(reload=True)
        self._listbox.change_focus(size, prevnode, coming_from='below',
                                   offset_inset = offset)
        # refresh the field add buttons, since the list of available keys has
        # changed
        fieldaddnode = self.get_child_node(self._fieldaddkey)
        fieldaddnode.get_widget(reload=True)

    def is_deletable(self):
        return self.get_value().is_deletable()

    def insert_child_node(self, key):
        """insert a node just prior to the given key"""
        # update the json first
        jsonnode = self.get_value()
        jsonnode.insert_child(key)
        # refresh the child key cache
        keys = self.get_child_keys(reload=True)
        for k in keys:
            self.get_child_node(k, reload=True)
        # change the focus to the new field.
        newnode = self.get_child_node(key)
        size = self._listbox._size
        offset, inset = self._listbox.get_focus_offset_inset(size)
        self._listbox.change_focus(size, newnode, coming_from='below',
                                   offset_inset = offset)
        # refresh the field add buttons, since the list of available keys has
        # changed
        if len(jsonnode.get_available_keys()) > 0:
            fieldaddnode = self.get_child_node(self._fieldaddkey)
            fieldaddnode.get_widget(reload=True)

    def insert_node(self):
        """ Insert a node before this one """
        parent = self.get_parent()
        parent.insert_child_node(self.get_key())

    def is_insertable(self):
        """ Can a node be inserted at this point in the tree? """
        return self.get_value().is_insertable()

    def get_title_max_length(self):
        """Get max length of child titles (not counting maps and seqs)"""
        maxlen = 0
        myval = self.get_value()
        if myval.is_type('array'):
            # we need to make room for the " #10" part of "item #10"
            numchild = len(self.get_value().get_children())
            addspace = len(str(numchild)) + 2
        else:
            addspace = 0
        for child in self.get_value().get_schema_node().get_children():
            if not child.is_type('array') and not child.is_type('object'):
                maxlen = max(maxlen, len(child.get_title())+addspace)
        return maxlen
    
    def change_child_key(self, oldkey, newkey):
        ParentNode.change_child_key(self, oldkey, newkey)
        jsonnode = self.get_value().change_child_key(oldkey, newkey)
        self.get_child_keys(reload=True)
        self.get_widget(reload=True)


class JsonFrame(TreeListBox):
    def __init__(self, jsonobj):
        self.json = jsonobj
        walker = TreeWalker(JsonWidgetParent(self.json, listbox=self))
        return super(self.__class__, self).__init__(walker)

    def keypress(self, size, key):
        # HACK: this is the only reliable way I could figure out how to get
        # this info to add_child_node
        self._size = size
        return self.__super.keypress(size, key)

