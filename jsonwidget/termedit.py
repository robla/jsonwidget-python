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


import threading
import sys
import os
import re
import json

try:
    import urwid.curses_display
    import urwid
except ImportError:
    msg = """
  jsonwidget.termedit requires urwid 0.98 or higher, which doesn't appear to be
  installed.  
  
  The latest version of urwid for all systems can be found at:
    http://excess.org/urwid/

  ...or in easy_install as "urwid"

  On Debian and Ubuntu, simply install 'python-urwid' (and install 
  'python-simpleparse' while you're at it).

"""
    sys.stderr.writelines(msg)
    sys.exit(2)

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
        return self.get_json_node().get_title() + ": "

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
        return str(self.get_json_node().get_data())

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


class FieldAddButtons(BaseJsonEditWidget):
    """ Add a button"""

    def load_inner_widget(self):
        jsonnode = self.get_node().get_parent().get_value()

        if jsonnode.get_schema_node().get_type() == 'seq':
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

        if(schemanode.get_type() == 'str'):
            if(schemanode.is_enum()):
                return EnumEditWidget(self)
            else:
                return GenericEditWidget(self)
        elif(schemanode.get_type() == 'int'):
            return IntEditWidget(self)
        elif(schemanode.get_type() == 'number'):
            return NumberEditWidget(self)
        elif(schemanode.get_type() == 'bool'):
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

class JsonWidgetParent(ParentNode):
    def __init__(self, jsonnode, parent=None, key=None, depth=None, 
                 listbox=None):
        key = jsonnode.get_key()
        depth = jsonnode.get_depth()
        self._fieldaddkey = FieldAddKey()
        self._listbox = listbox
        ParentNode.__init__(self, jsonnode, key=key, parent=parent, 
                            depth=depth)

    def load_widget(self):
        return ArrayEditWidget(self)

    def load_child_keys(self):
        jsonnode = self.get_value()
        keys = jsonnode.get_child_keys()
        if len(jsonnode.get_available_keys()) > 0:
            fieldaddkey = self._fieldaddkey
            keys.append(fieldaddkey)
        return keys

    def load_child_node(self, key):
        depth = self.get_depth() + 1
        if isinstance(key, FieldAddKey):
            return FieldAddNode(None, parent=self, depth=depth, key=key)
        else:
            jsonnode = self.get_value().get_child(key)
            schemanode = jsonnode.get_schema_node()
            nodetype = schemanode.get_type()
            if (nodetype == 'map') or (nodetype == 'seq'):
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

    def get_title_max_length(self):
        """Get max length of child titles (not counting maps and seqs)"""
        maxlen = 0
        mytype = self.get_value().get_type()
        if mytype == 'seq':
            # we need to make room for the " #10" part of "item #10"
            numchild = len(self.get_value().get_children())
            addspace = len(str(numchild)) + 2
        else:
            addspace = 0
        for child in self.get_value().get_schema_node().get_children():
            childtype = child.get_type()
            if not childtype == 'seq' and not childtype == 'map':
                maxlen = max(maxlen, len(child.get_title())+addspace)
        return maxlen


class JsonPinotFile(PinotFile):
    '''Glue to between PinotFile and underlying JSON object'''

    def __init__(self, jsonfile=None, schemafile=None):
        if jsonfile is None or os.access(jsonfile, os.R_OK):
            # file exists, and we can read it (or we're just passing "None")
            self.json = JsonNode(filename=jsonfile, schemafile=schemafile)
            self.schema = self.json.get_schema_node()
        elif os.access(jsonfile, os.F_OK):
            # file exists, but can't read it
            sys.stderr.write("Cannot access file \"%s\" (check permissions)\n" %
                             jsonfile)
            sys.exit(os.EX_NOINPUT)
        else:
            # must be a new file
            self.json = JsonNode(filename=None, schemafile=schemafile)
            self.schema = self.json.get_schema_node()
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

    def get_schema_display_text(self):
        filename = self.schema.get_filename()
        if filename is None:
            filename = "(new file)"
        else:
            filename = os.path.basename(filename)
        return "schema: " + filename


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


class JsonFileEditor(PinotFileEditor):
    """
    JSON editor specific commands
    These routines deal with the specifics of a JSON editor.
    """
    def __init__(self, jsonfile=None, schemafile=None, fileobj=None,
                 program_name="JsonWidget", monochrome=True):
        if fileobj is None:
            try:
                self.file = JsonPinotFile(jsonfile=jsonfile, schemafile=schemafile)
            except JsonNodeError as inst:
                sys.stderr.writelines(program_name + " error:\n")
                sys.stderr.writelines(str(inst) + "\n\n")
                sys.exit(2)
        else:
            self.file = fileobj

        self.json = self.file.get_json()
        self.schema = self.json.get_schema_node()
        self.listbox = JsonFrame(self.json)
        PinotFileEditor.__init__(self, program_name=program_name, 
                                 unhandled_input=self.unhandled_input)
        self.set_default_footer_helpitems([("^W", "Write/Save"), 
                                           ("^X", "Exit"),
                                           ("^D", "Delete Item")])
        if monochrome:
            urwid.curses_display.curses.has_colors = lambda: False



    def handle_delete_node_request(self):
        """Handle ctrl d - "delete item"."""
        editor = self
        widget, node = self.listbox.get_focus()

        if node.is_deletable():
            widget.set_selected()
            widget.update_w()
            def delete_func():
                widget.set_selected(False)
                widget.update_w()
                return editor.handle_delete_node()
            def cancel_delete():
                widget.set_selected(False)
                widget.update_w()
                editor.cleanup_delete_request()
            msg = "Delete %s? " % node.get_value().get_title()
            self.yes_no_question(msg,
                                 yesfunc=delete_func,
                                 nofunc=cancel_delete,
                                 cancelfunc=cancel_delete)
        else:
            if isinstance(node, FieldAddNode):
                nodemsg = 'Cannot delete "add field" buttons'
            else:
                nodemsg = ("%s is a required field" % 
                           node.get_value().get_title())
            delparent = node.get_parent()
            while delparent is not None and not delparent.is_deletable():
                delparent = delparent.get_parent()
            if delparent is not None:
                parenttitle = delparent.get_value().get_title()
                msg = ("%s of %s, try deleting %s instead" % 
                       (nodemsg, parenttitle, parenttitle))
                self.listbox.set_focus(delparent)
            else:
                msg = nodemsg
            self.cleanup_delete_request()
            self.display_notification(msg)


    def handle_delete_node(self):
        widget, node = self.listbox.get_focus()
        node.delete_node()
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

    def unhandled_input(self, input):
        """ Attach handlers for keyboard commands here. """
        if input == 'ctrl x':
            if self.file.is_saved():
                self.handle_exit()
                return None
            else:
                self.handle_exit_request()
                return None
        elif input == 'ctrl w':
            self.handle_write_to_request()
            return None
        elif input == 'ctrl d':
            self.handle_delete_node_request()
            return None
        else:
            return input

    def get_center_header_text(self):
        filename = self.file.get_filename_text()
        if self.file.is_saved() is False:
            filename += " (modified)"
        return filename

    def get_right_header_text(self):
        return self.file.get_schema_display_text()


class JsonDataEditor(JsonFileEditor):
    """
    This is an editor for in-memory data instead of a file
    """
    def __init__(self, jsonnode=None, jsondata=None, schemafile=None, 
                 schemadata=None, schemanode=None, program_name="JsonWidget", 
                 monochrome=True):
        if jsonnode is None:
            self.json = JsonNode(data=jsondata, schemafile=schemafile, 
                                 schemadata=schemadata, schemanode=schemanode)
        else:
            self.json = jsonnode
        self.schema = self.json.get_schema_node()
        self.listbox = JsonFrame(self.json)
        PinotFileEditor.__init__(self, program_name=program_name, 
                                 unhandled_input=self.unhandled_input)
        self.set_default_footer_helpitems([("^W", "Write/Save"), 
                                           ("^X", "Exit"),
                                           ("^D", "Delete Item")])
        if monochrome:
            urwid.curses_display.curses.has_colors = lambda: False

    def unhandled_input(self, input):
        """ Attach handlers for keyboard commands here. """
        if input == 'ctrl x':
            self.handle_exit()
        elif input == 'ctrl d':
            self.handle_delete_node_request()
            return None
        else:
            return input

    def get_center_header_text(self):
        return ""

    def get_right_header_text(self):
        return ""


