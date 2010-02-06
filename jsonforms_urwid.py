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


class EntryForm:
    """The top-level form where all of the widgets get placed."""

    # I'm guessing this should get replaced with a MainLoop when this moves
    # to urwid 0.99.

    def __init__(self, json, program_name="JsonWidget"):
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
        self.json = json
        self.schema = json.get_schema_node()
        self.endstatusmessage = ""
        self.progname = program_name
        self.footertimer = None

    def run(self):
        widget = get_schema_widget(self.json)
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

    def get_header(self):
        headerleft = urwid.Text(self.progname, align='left')
        filename = self.json.get_filename_text()
        if self.json.is_saved() is False:
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
            helptext = [("^W", "Write/Save"), ("^X", "Exit")]
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
                if key == 'window resize':
                    size = self.ui.get_cols_rows()
                elif key == 'ctrl x':
                    if self.json.is_saved():
                        self.handle_exit()
                    else:
                        self.handle_exit_request()
                elif key == 'ctrl w':
                    self.handle_write_to_request()
                else:
                    self.view.keypress(size, key)

    def handle_exit_request(self):
        entryform = self

        class CallbackEdit(urwid.Edit):

            def keypress(self, (maxcol, ), key):
                if key == 'y':
                    if entryform.json.get_filename() is None:
                        entryform.cleanup_user_question()
                        entryform.handle_write_to_request(exit_on_save=True)
                    else:
                        entryform.handle_save()
                        msg = "Saved " + entryform.json.get_filename() + "\n"
                        entryform.append_end_status_message(msg)
                        entryform.handle_exit()
                elif key == 'n':
                    entryform.handle_exit()
                elif key == 'esc':
                    entryform.cleanup_user_question()
        prompt = CallbackEdit(
            'Save changes (ANSWERING "No" WILL DESTROY CHANGES) ? ', "")
        self.view.set_focus("footer")
        helptext = [("Y", "Yes"), ("N", "No"), ("ESC", "Cancel")]
        footerstatus = self.get_footer_status_widget(prompt, active=True)
        footerhelp = self.get_footer_help_widget(helptext=helptext)
        self.set_footer([footerstatus, footerhelp])

    def handle_write_to_request(self, exit_on_save=False):
        entryform = self

        class CallbackEdit(urwid.Edit):

            def keypress(self, (maxcol, ), key):
                urwid.Edit.keypress(self, (maxcol, ), key)
                if key == 'enter':
                    currentfilename = entryform.json.get_filename()
                    entryform.json.set_filename(self.get_edit_text())
                    try:
                        entryform.handle_save()
                        msg = "Saved " + entryform.json.get_filename()
                    except:
                        msg = "FAILED TO WRITE " + entryform.json.get_filename()
                        entryform.json.set_filename(currentfilename)
                    else:
                        if exit_on_save:
                            msg += "\n"
                            entryform.append_end_status_message(msg)
                            entryform.handle_exit()
                    entryform.handle_save_status(msg)
                elif key == 'esc':
                    entryform.cleanup_user_question()
        filename = entryform.json.get_filename()
        if filename is None:
            filename = ""
        prompt = CallbackEdit('File name to write to? ', filename)
        self.view.set_focus("footer")
        helptext = [("Enter", "Confirm"), ("ESC", "Cancel")]
        footerstatus = self.get_footer_status_widget(prompt, active=True)
        footerhelp = self.get_footer_help_widget(helptext=helptext)
        self.set_footer([footerstatus, footerhelp])

    def handle_save(self):
        self.json.save_to_file()

    def handle_save_status(self, msg):
        self.set_header()
        self.view.set_focus("body")
        msg = "  " + msg + "  "
        msgwidget = urwid.Text(('footerstatusactive', msg), align='center')
        footerstatus = self.get_footer_status_widget(msgwidget)
        footerhelp = self.get_footer_help_widget()
        self.set_footer([footerstatus, footerhelp])
        self.set_footer_status_timer(5.0)

    def handle_exit(self):
        raise JsonWidgetExit()

    def cleanup_user_question(self):
        self.view.set_focus("body")
        self.set_default_footer()

    def append_end_status_message(self, status):
        self.endstatusmessage += status

    def get_end_status_message(self):
        return self.endstatusmessage
