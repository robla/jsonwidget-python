#!/usr/bin/python
# Pinot - set of classes for building a pine/pico/nano-inspired editor
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.
#
# classes:
# RetroMainLoop - Main event loop base routines
# PinotUserInterface - pine/pico/nano-inspired user interface routines
# PinotFileEditor - Standalone file editor methods (load file, save file)
#
# The chain of classes below are the result of breaking up one monolithic
# class broken out from jsonwdiget.   As of this writing, there isn't clean 
# separation between these, and there's a few remaining ties to json, but 
# future work will strive to separate these more cleanly.
#


class PinotError(RuntimeError):
    pass


class PinotExit(Exception):
    pass


import urwid.curses_display
import urwid
import threading
import sys
import os


from jsonwidget.schema import *
from jsonwidget.jsonnode import *
from jsonwidget.pinot import *


class RetroMainLoop(object):
    """
    Main event loop base routines
    I'm guessing this should get replaced with a MainLoop when this moves
    to urwid 0.99.
    """

    def __init__(self, program_name="RetroMainLoop", unhandled_input=None):
        self.ui = urwid.curses_display.Screen()
        self.ui.register_palette([
            ('body', 'black', 'light gray'),
            ('selected', 'black', 'dark green', ('bold','underline')),
            ('focus', 'light gray', 'dark blue', 'standout'),
            ('selected focus', 'yellow', 'dark cyan', 
                    ('bold','standout','underline')),
            ('head', 'yellow', 'black', 'standout'),
            ('foot', 'light gray', 'black'),
            ('key', 'light cyan', 'black','underline'),
            ('title', 'white', 'black', 'bold'),
            ('dirmark', 'black', 'dark cyan', 'bold'),
            ('flag', 'dark gray', 'light gray'),
            ('error', 'dark red', 'light gray'),
 
            ('default', 'default', 'default'),
            ('editfield', 'light gray', 'dark blue', 'underline'),
            ('editfieldfocus', 'white', 'dark red', ('underline','standout')),
            ('selected', 'white', 'dark red', 'standout'),
            ('header', 'light gray', 'dark red', 'standout'),
            ('notificationdormant', 'light gray', 'dark blue'),
            ('notificationactive', 'light gray', 'dark blue', 'standout'),
            ('notificationedit', 'light gray', 'dark blue'),
            ('footerkeys', 'light gray', 'dark blue', 'standout'),
            ('footerhelp', 'light gray', 'dark blue')])
        self.endstatusmessage = ""
        self.progname = program_name
        self.notificationtimer = None
        self._unhandled_input = unhandled_input

    def run(self):
        header = self.get_header()
        body = self.get_body()
        footer = self.get_footer()

        self.view = urwid.Frame(body, header=header, footer=footer)

        try:
            self.ui.run_wrapper(self.run_loop)
        except PinotExit:
            pass

        # need to clear this timer, or else we have to wait for the timer
        # before the app exits
        self.clear_notification_timer()
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
                else:
                    if self._unhandled_input is not None:
                        key = self._unhandled_input(key)
                    if key is not None:
                        self.view.keypress(size, key)


class PinotUserInterface(RetroMainLoop):
    """
    pine/pico/nano-inspired user interface routines
    These are the routines that implement the standard look-and-feel of the
    editor - header and footer format, status messages, yes/no prompts
    """

    def __init__(self, **kwargs):
        self._default_footer_helpitems = None
        RetroMainLoop.__init__(self, **kwargs)

    def get_header(self):
        headerleft = urwid.Text(self.get_left_header_text(), align='left')
        headercenter = urwid.Text(self.get_center_header_text(), 
                                  align='center')
        headerright = urwid.Text(self.get_right_header_text(), align='right')

        header1columns = urwid.Columns([headerleft, headercenter, headerright])
        header1padded = urwid.Padding(header1columns, ('fixed left', 2),
                                      ('fixed right', 2), 20)
        header1 = urwid.AttrWrap(header1padded, "header")
        header2 = urwid.Text("")
        return urwid.Pile([header1, header2])

    def get_left_header_text(self):
        return self.progname

    def get_center_header_text(self):
        filename = self.file.get_filename_text()
        return filename

    def get_right_header_text(self):
        if self.file.is_saved() is False:
            righttext = "(modified)"
        else:
            righttext = ""
        return righttext

    def set_header(self):
        header = self.get_header()
        self.view.set_header(header)

    def set_body(self):
        body = self.get_body()
        self.view.set_body(body)
        # Test if this is really needed
        self.ui.clear()

    def get_body(self):
        return self.listbox

    def set_footer(self, widgets):
        self.clear_notification_timer()
        self.view.set_footer(urwid.Pile(widgets))

    def set_notification_timer(self, time):
        self.notificationtimer = threading.Timer(time, self.set_default_footer)
        self.notificationtimer.start()

    def set_default_footer(self):
        self.view.set_footer(self.get_footer())
        self.ui.clear()

    def set_default_footer_helpitems(self, helpitems=None):
        self._default_footer_helpitems = helpitems
        
    def get_footer(self):
        notification = self.get_notification_widget()
        footerhelp = self.get_footer_help_widget()
        return urwid.Pile([notification, footerhelp])
   
    def clear_notification_timer(self):
        if self.notificationtimer is not None:
            self.notificationtimer.cancel()

    def get_notification_widget(self, widget=None, active=False):
        if widget is None:
            widget = urwid.Text("")

        if(active):
            wrapped = urwid.AttrWrap(widget, "notificationactive")
        else:
            wrapped = urwid.AttrWrap(widget, "notificationdormant")
        return urwid.Pile([wrapped])

    def get_footer_help_widget(self, helptext=None, rows=2):
        if(helptext is None):
            helptext = self._default_footer_helpitems
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
        notification = self.get_notification_widget(prompt, active=True)
        footerhelp = self.get_footer_help_widget(helptext=helptext)
        self.set_footer([notification, footerhelp])

    def display_notification(self, msg):
        """Generic notification on a 5 second timer"""
        self.set_header()
        self.view.set_focus("body")
        msg = "  " + msg + "  "
        msgwidget = urwid.Text(('notificationactive', msg), align='center')
        notification = self.get_notification_widget(msgwidget)
        footerhelp = self.get_footer_help_widget()
        self.set_footer([notification, footerhelp])
        self.set_notification_timer(5.0)

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
                    entryform.display_notification(msg)
                elif key == 'esc':
                    entryform.cleanup_user_question()
        filename = entryform.file.get_filename()
        if filename is None:
            filename = ""
        prompt = CallbackEdit('File name to write to? ', filename)
        self.view.set_focus("footer")
        helptext = [("Enter", "Confirm"), ("ESC", "Cancel")]
        notification = self.get_notification_widget(prompt, active=True)
        footerhelp = self.get_footer_help_widget(helptext=helptext)
        self.set_footer([notification, footerhelp])

    def handle_exit_request(self):
        """Handle ctrl x - "exit"."""
        self.yes_no_question(
            'Save changes (ANSWERING "No" WILL DESTROY CHANGES) ? ',
            yesfunc=self.handle_save_and_exit,
            nofunc=self.handle_exit)

    def handle_save(self):
        self.file.save_to_file()

    def handle_save_and_exit(self):
        if self.file.get_filename() is None:
            self.cleanup_user_question()
            self.handle_write_to_request(exit_on_save=True)
        else:
            self.handle_save()
            msg = "Saved " + self.file.get_filename() + "\n"
            self.append_end_status_message(msg)
            self.handle_exit()

    def handle_exit(self):
        raise PinotExit()

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



