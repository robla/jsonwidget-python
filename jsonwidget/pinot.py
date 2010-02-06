#!/usr/bin/python
# Library for building urwid-based forms from JSON schemas
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.


class Error(RuntimeError):
    pass

import json
import urwid.curses_display
import urwid
import threading
import sys
import os


from jsonwidget.schema import *
from jsonwidget.jsonnode import *
from jsonwidget.pinot import *


# The chain of classes below are the result of breaking up one monolithic
# class.   As of this writing, there isn't clean separation between these, but 
# future work will strive to separate these more cleanly.
    
# Sections:
# RetroMainLoop - Main event loop base routines
# PinotUserInterface - pine/pico/nano-inspired user interface routines
# PinotFileEditor - Standalone file editor methods (load file, save file)
# JsonEditor - JSON editor-specific commands


class RetroMainLoop(object):
    """
    Main event loop base routines
    I'm guessing this should get replaced with a MainLoop when this moves
    to urwid 0.99.
    """

    def __init__(self, program_name="RetroMainLoop"):
        self.ui = urwid.curses_display.Screen()
        self.ui.register_palette([
            ('default', 'default', 'default'),
            ('editfield', 'light gray', 'dark blue', 'underline'),
            ('editfieldfocus', 'white', 'dark red', 'underline'),
            ('header', 'light gray', 'dark red', 'standout'),
            ('footerstatusdormant', 'light gray', 'dark blue'),
            ('footerstatusactive', 'light gray', 'dark blue', 'standout'),
            ('footerstatusedit', 'light gray', 'dark blue'),
            ('footerkeys', 'light gray', 'dark blue', 'standout'),
            ('footerhelp', 'light gray', 'dark blue')])
        self.endstatusmessage = ""
        self.progname = program_name
        self.footertimer = None

    def run(self):
        widget = self.file.get_edit_widget()
        self.walker = urwid.SimpleListWalker([widget])
        listbox = urwid.ListBox(self.walker)
        header = self.get_header()
        footerstatus = self.get_footer_status_widget()
        footerhelp = self.get_footer_help_widget()
        footer = urwid.Pile([footerstatus, footerhelp])

        self.view = urwid.Frame(listbox, header=header, footer=footer)

        try:
            self.ui.run_wrapper(self.run_loop)
        except JsonWidgetExit:
            pass

        # need to clear this timer, or else we have to wait for the timer
        # before the app exits
        self.clear_footer_status_timer()
        if not self.endstatusmessage == "":
            print self.endstatusmessage,

    def run_loop(self):
        size = self.ui.get_cols_rows()
        while(True):
            self.set_header()
            canvas = self.view.render(size, focus=1)
            self.ui.draw_screen(size, canvas)
            keys = None
            while(keys == None):
                # self.ui.get_input() blocks for max_wait time, default 0.5 sec
                # use self.ui.set_input_timeouts() to change the default
                try:
                    keys = self.ui.get_input()
                except KeyboardInterrupt:
                    pass
            for key in keys:
                # TODO: fix layer violation here.  ctrl keys should be handled
                # in subclasses
                if key == 'window resize':
                    size = self.ui.get_cols_rows()
                elif key == 'ctrl x':
                    if self.file.is_saved():
                        self.handle_exit()
                    else:
                        self.handle_exit_request()
                elif key == 'ctrl w':
                    self.handle_write_to_request()
                elif key == 'ctrl d':
                    self.handle_delete_node_request()
                else:
                    self.view.keypress(size, key)


class PinotUserInterface(RetroMainLoop):
    """
    pine/pico/nano-inspired user interface routines
    These are the routines that implement the standard look-and-feel of the
    editor - header and footer format, status messages, yes/no prompts
    """

    def get_header(self):
        headerleft = urwid.Text(self.progname, align='left')
        filename = self.file.get_filename_text()
        if self.file.is_saved() is False:
            filename += " (modified)"
        headercenter = urwid.Text(filename, align='center')
        headerright = urwid.Text("schema: " + self.schema.get_filename_text(),
                                 align='right')

        header1columns = urwid.Columns([headerleft, headercenter, headerright])
        header1padded = urwid.Padding(header1columns, ('fixed left', 2),
                                      ('fixed right', 2), 20)
        header1 = urwid.AttrWrap(header1padded, "header")
        header2 = urwid.Text("")
        return urwid.Pile([header1, header2])

    def set_header(self):
        header = self.get_header()
        self.view.set_header(header)

    def set_footer(self, widgets):
        self.clear_footer_status_timer()
        self.view.set_footer(urwid.Pile(widgets))

    def set_footer_status_timer(self, time):
        self.footertimer = threading.Timer(time, self.set_default_footer)
        self.footertimer.start()

    def set_default_footer(self):
        footerstatus = self.get_footer_status_widget()
        footerhelp = self.get_footer_help_widget()
        self.view.set_footer(urwid.Pile([footerstatus, footerhelp]))
        self.ui.clear()

    def clear_footer_status_timer(self):
        if self.footertimer is not None:
            self.footertimer.cancel()

    def get_footer_status_widget(self, widget=None, active=False):
        if widget is None:
            widget = urwid.Text("")

        if(active):
            wrapped = urwid.AttrWrap(widget, "footerstatusactive")
        else:
            wrapped = urwid.AttrWrap(widget, "footerstatusdormant")
        return urwid.Pile([wrapped])

    def get_footer_help_widget(self, helptext=None, rows=2):
        if(helptext is None):
            helptext = [("^W", "Write/Save"), ("^X", "Exit"),
                        ("^D", "Delete Node")]
        numcols = (len(helptext) + 1) / rows
        helpcolumns = []
        for i in range(numcols):
            helpcolumns.append([])

        # populate the rows top to bottom, then left to right
        i = 0
        col = 0
        for item in helptext:
            textitem = urwid.Text([('footerkeys', item[0]), " ", item[1]])
            helpcolumns[col].append(textitem)
            i += 1
            col = i / rows

        # now stuff everything into column widgets
        helpwidgets = []
        for helpcol in helpcolumns:
            helpwidgets.append(urwid.Pile(helpcol))
        return urwid.Columns(helpwidgets)

    def yes_no_question(self, prompt, yesfunc=None, nofunc=None, 
                        cancelfunc=None):
        entryform = self

        class CallbackEdit(urwid.Edit):

            def keypress(self, (maxcol, ), key):
                if key == 'y':
                    if yesfunc is None:
                        entryform.cleanup_user_question()
                    else:
                        yesfunc()
                elif key == 'n':
                    if nofunc is None:
                        entryform.cleanup_user_question()
                    else:
                        nofunc()
                elif key == 'esc':
                    if cancelfunc is None:
                        entryform.cleanup_user_question()
                    else:
                        cancelfunc()
        prompt = CallbackEdit(prompt, "")
        self.view.set_focus("footer")
        helptext = [("Y", "Yes"), ("N", "No"), ("ESC", "Cancel")]
        footerstatus = self.get_footer_status_widget(prompt, active=True)
        footerhelp = self.get_footer_help_widget(helptext=helptext)
        self.set_footer([footerstatus, footerhelp])

    def handle_save_status(self, msg):
        """Generic status message on a 5 second timer"""
        # TODO: rename to something more generic
        self.set_header()
        self.view.set_focus("body")
        msg = "  " + msg + "  "
        msgwidget = urwid.Text(('footerstatusactive', msg), align='center')
        footerstatus = self.get_footer_status_widget(msgwidget)
        footerhelp = self.get_footer_help_widget()
        self.set_footer([footerstatus, footerhelp])
        self.set_footer_status_timer(5.0)

    def cleanup_user_question(self):
        self.view.set_focus("body")
        self.set_default_footer()


class PinotFileEditor(PinotUserInterface):
    """
    Standalone editor specific methods
    These routines deal with the specifics of an editor that loads/saves
    files.  There shouldn't be anything JSON-specific in this
    """

    def handle_write_to_request(self, exit_on_save=False):
        """Handle ctrl w - "write/save"."""
        entryform = self

        class CallbackEdit(urwid.Edit):

            def keypress(self, (maxcol, ), key):
                urwid.Edit.keypress(self, (maxcol, ), key)
                if key == 'enter':
                    currentfilename = entryform.file.get_filename()
                    entryform.file.set_filename(self.get_edit_text())
                    try:
                        entryform.handle_save()
                        msg = "Saved " + entryform.file.get_filename()
                    except:
                        msg = "FAILED TO WRITE " + entryform.file.get_filename()
                        entryform.file.set_filename(currentfilename)
                    else:
                        if exit_on_save:
                            msg += "\n"
                            entryform.append_end_status_message(msg)
                            entryform.handle_exit()
                    entryform.handle_save_status(msg)
                elif key == 'esc':
                    entryform.cleanup_user_question()
        filename = entryform.file.get_filename()
        if filename is None:
            filename = ""
        prompt = CallbackEdit('File name to write to? ', filename)
        self.view.set_focus("footer")
        helptext = [("Enter", "Confirm"), ("ESC", "Cancel")]
        footerstatus = self.get_footer_status_widget(prompt, active=True)
        footerhelp = self.get_footer_help_widget(helptext=helptext)
        self.set_footer([footerstatus, footerhelp])

    def handle_exit_request(self):
        """Handle ctrl x - "exit"."""
        self.yes_no_question(
            'Save changes (ANSWERING "No" WILL DESTROY CHANGES) ? ',
            yesfunc=self.handle_save_and_exit,
            nofunc=self.handle_exit)

    def handle_save(self):
        self.json.save_to_file()

    def handle_save_and_exit(self):
        if self.json.get_filename() is None:
            self.cleanup_user_question()
            self.handle_write_to_request(exit_on_save=True)
        else:
            self.handle_save()
            msg = "Saved " + self.json.get_filename() + "\n"
            self.append_end_status_message(msg)
            self.handle_exit()

    def handle_exit(self):
        raise JsonWidgetExit()

    def append_end_status_message(self, status):
        self.endstatusmessage += status

    def get_end_status_message(self):
        return self.endstatusmessage

class PinotFile(object):
    '''Abstract base class'''

    def get_filename(self):
        pass

    def save_to_file(self):
        pass

    def set_filename(self, name):
        pass

    def get_filename_text(self):
        pass

    def is_saved(self):
        pass

    def get_edit_widget(self):
        pass

