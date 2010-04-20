#!/usr/bin/python
# Library for building urwid-based forms from JSON schemas.
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.
#
# This file contains the chrome and file handling capability for urwid-specific
# file editors.


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
from jsonwidget.termwidgets import *


class JsonPinotFile(PinotFile):
    '''Glue to between PinotFile and underlying JSON object'''

    def __init__(self, jsonfile=None, schemafile=None, schemaobj=None):
        if jsonfile is None or os.access(jsonfile, os.R_OK):
            # file exists, and we can read it (or we're just passing "None")
            self.json = JsonNode(filename=jsonfile, schemafile=schemafile,
                schemanode=schemaobj)
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
            return "(auto-generated schema)"
        else:
            return "schema: " + os.path.basename(filename)


class JsonFileEditor(PinotFileEditor):
    """
    JSON editor specific commands
    These routines deal with the specifics of a JSON editor.
    """
    def __init__(self, jsonfile=None, schemafile=None, fileobj=None, 
                 schemaobj=None, program_name="JsonWidget", monochrome=True):
        if fileobj is None:
            self.file = JsonPinotFile(jsonfile=jsonfile, 
                                      schemafile=schemafile,
                                      schemaobj=schemaobj)
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


