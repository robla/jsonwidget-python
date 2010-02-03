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

from floatedit import FloatEdit

# Class factory for UI widgets.
# node: either a SchemaNode or JsonNode
# returns the appropriate UI widget
def get_schema_widget( node ):
    if(isinstance(node, JsonNode)):
        jsonnode=node
    else:
        raise Error("Type error: %s" % type(node).__name__) 

    # we want to make sure that we use a schema-appropriate edit widget, so
    # don't use jsonnode.getType() directly.
    schemanode=jsonnode.getSchemaNode()

    if(schemanode.getType()=='map'):
        return ArrayEditWidget(jsonnode)
    elif(schemanode.getType()=='seq'):
        return ArrayEditWidget(jsonnode)
    elif(schemanode.getType()=='str'):
        if(schemanode.isEnum()):
            return EnumEditWidget(jsonnode)
        else:
            return GenericEditWidget(jsonnode)
    elif(schemanode.getType()=='int'):
        return IntEditWidget(jsonnode)
    elif(schemanode.getType()=='number'):
        return NumberEditWidget(jsonnode)
    elif(schemanode.getType()=='bool'):
        return BoolEditWidget(jsonnode)
    else:
        return GenericEditWidget(jsonnode)

# Series of editing widgets follows, each appropriate to a datatype or two

# Map and Seq edit widget and container
class ArrayEditWidget( urwid.WidgetWrap ):
    def __init__(self, jsonnode):
        self.json = jsonnode
        self.schema = jsonnode.getSchemaNode()
        maparray=[]
        maparray.append(urwid.Text( self.json.getTitle() + ": " ))
        leftmargin = urwid.Text( "" )

        mapfields = self.buildPile()
        self.indentedmap = urwid.Columns( [ ('fixed', 2, leftmargin), mapfields ] )
        maparray.append(self.indentedmap)
        mappile=urwid.Pile(maparray)
        return urwid.WidgetWrap.__init__(self, mappile)

    def addNode(self, key):
        self.json.addChild(key)
        self.indentedmap.widget_list[1]=self.buildPile()

    # build a vertically stacked array of widgets
    def buildPile(self):
        pilearray=[]

        for child in self.json.getChildren():
            pilearray.append(get_schema_widget(child))
        pilearray.append(FieldAddButtons(self,self.json))

        return urwid.Pile( pilearray )

# generic widget used for free text entry (e.g. strings)
class GenericEditWidget( urwid.WidgetWrap ):
    def __init__(self, jsonnode):
        self.schema = jsonnode.getSchemaNode()
        self.json = jsonnode
        editcaption = urwid.Text( ('default', self.json.getTitle() + ": ") )
        editfield = self.getEditFieldWidget()
        editpair = urwid.Columns ( [ ('fixed', 20, editcaption), editfield ] )
        urwid.WidgetWrap.__init__(self, editpair)

    def getEditFieldWidget(self):
        thiswidget=self
        # closure which effectively gives this object a callback when the 
        # text of the widget changes.  This was in lieu of figuring out how to
        # properly use Signals, which may need to wait until I upgrade to using
        # urwid 0.99.
        class CallbackEdit(urwid.Edit):
            def set_edit_text(self, text):
                urwid.Edit.set_edit_text(self, text)
                thiswidget.json.setData(text)
        innerwidget=CallbackEdit("", str(self.json.getData()))
        return urwid.AttrWrap(innerwidget, 'editfield', 'editfieldfocus')

# Integer edit widget
class IntEditWidget( GenericEditWidget ):
    def getEditFieldWidget(self):
        innerwidget=urwid.IntEdit("", self.json.getData())
        return urwid.AttrWrap(innerwidget, 'editfield', 'editfieldfocus')

# Number edit widget
class NumberEditWidget( GenericEditWidget ):
    def getEditFieldWidget(self):
        innerwidget=FloatEdit("", self.json.getData())
        return urwid.AttrWrap(innerwidget, 'editfield', 'editfieldfocus')

# Boolean edit widget
class BoolEditWidget( GenericEditWidget ):
    def getEditFieldWidget(self):
        return urwid.CheckBox("", self.json.getData())

# Enumerated string edit widget
class EnumEditWidget( GenericEditWidget ):
    def getEditFieldWidget(self):
        options=[]
        self.radiolist = []
        for option in self.schema.enumOptions():
            if(self.json.getData()==option):
                state=True
            else:
                state=False
            options.append(urwid.RadioButton(self.radiolist, option, state=state))
        return urwid.GridFlow( options, 13,3,1, 'left')

# Add a button
class FieldAddButtons( urwid.WidgetWrap ):
    def __init__(self, parentwidget, json):
        self.parentwidget = parentwidget
        self.json = json
        caption = urwid.Text( ('default', "Add fields: ") )
        buttonfield = self.getButtons()
        editpair = urwid.Columns ( [ ('fixed', 20, caption), buttonfield ] )
        urwid.WidgetWrap.__init__(self, editpair)

    def getButtons(self):
        parentwidget=self.parentwidget
        buttons=[]
        def on_press(button, user_data=None):
            parentwidget.addNode(user_data['key'])
        for key in self.json.getAvailableKeys():
            fieldname = self.json.getChildTitle(key)
            buttons.append(urwid.Button(fieldname,on_press,{'key':key}))
        #TODO: remove hard coded widths
        return urwid.GridFlow( buttons, 13,3,1, 'left')

class JsonWidgetExit(Exception):
    pass

# the top-level form where all of the widgets get placed.
# I'm guessing this should get replaced with a MainLoop when this moves to urwid
# 0.99.
class EntryForm:
    def __init__(self, json, program_name="JsonWidget"):
        self.ui = urwid.curses_display.Screen()
        self.ui.register_palette( [ ('default', 'default', 'default'), 
                                    ('editfield', 'light gray', 'dark blue', 'underline'),
                                    ('editfieldfocus', 'white', 'dark red', 'underline'),
                                    ('header', 'light gray', 'dark red', 'standout'),
                                    ('footerstatusdormant', 'light gray', 'dark blue'),
                                    ('footerstatusactive', 'light gray', 'dark blue', 'standout'),
                                    ('footerstatusedit', 'light gray', 'dark blue'),
                                    ('footerkeys', 'light gray', 'dark blue', 'standout'),
                                    ('footerhelp', 'light gray', 'dark blue') ] )
        self.json = json
        self.schema = json.getSchemaNode()
        self.endstatusmessage = ""
        self.progname = program_name

    def run(self):
        widget = get_schema_widget(self.json)
        self.walker = urwid.SimpleListWalker( [ widget ] )
        listbox = urwid.ListBox( self.walker )
        self.headerleft = urwid.Text( self.progname, align='left' )
        self.headercenter = urwid.Text( self.json.getFilenameText(), align='center' )
        self.headerright = urwid.Text( "schema: "+self.schema.getFilenameText(), align='right' )

        header1columns = urwid.Columns([self.headerleft, 
                                        self.headercenter, 
                                        self.headerright])
        header1padded = urwid.Padding (header1columns, ('fixed left',2), 
                                       ('fixed right',2), 20 )
        self.header1 = urwid.AttrWrap(header1padded , "header")
        self.header2 = urwid.Text("")
        self.header = urwid.Pile([self.header1, self.header2])

        self.footerstatus = self.getFooterStatusWidget()
        self.footerhelp = self.getFooterHelpWidget()
        self.footer = urwid.Pile( [self.footerstatus, self.footerhelp] )

        self.view = urwid.Frame( listbox, header=self.header, footer=self.footer )

        self.exitnow = False

        try:
            self.ui.run_wrapper( self.runLoop )
        except JsonWidgetExit:
            pass
            
        print self.endstatusmessage,

    def getFooterStatusWidget(self, widget=None, active=False): 
        if widget is None:
            widget=urwid.Text("")

        if(active):
            wrapped=urwid.AttrWrap(widget, "footerstatusactive")
        else:
            wrapped=urwid.AttrWrap(widget, "footerstatusdormant")
        return urwid.Pile([wrapped])

    def getFooterHelpWidget(self, helptext=None, rows=2):
        if(helptext is None):
            helptext =  [("^W","Write/Save"),("^X","Exit")]
        numcols=(len(helptext)+1)/rows
        helpcolumns=[]
        for i in range(numcols):
            helpcolumns.append([])

        # populate the rows top to bottom, then left to right
        i=0; col=0
        for item in helptext:
            textitem=urwid.Text([('footerkeys', item[0]), " ", item[1]])
            helpcolumns[col].append(textitem)
            i+=1; col=i/rows

        # now stuff everything into column widgets
        helpwidgets=[]
        for helpcol in helpcolumns:
            helpwidgets.append(urwid.Pile(helpcol))
        return urwid.Columns(helpwidgets)

    def runLoop(self):
        size = self.ui.get_cols_rows()
        while(True):
            canvas = self.view.render( size, focus=1 )
            self.ui.draw_screen( size, canvas )
            keys = None
            while(keys == None):
                # self.ui.get_input() blocks for max_wait time, default 0.5 sec
                # use self.ui.set_input_timeouts() to change the default
                try:
                    keys = self.ui.get_input()
                except KeyboardInterrupt:
                    pass
                if(self.exitnow):
                    return
            for key in keys:
                if key == 'window resize':
                    size = self.ui.get_cols_rows()
                elif key == 'ctrl x':
                    self.handleExitRequest()
                elif key == 'ctrl s':
                    # this isn't functional yet...need to trap ctrl s first
                    self.handleSave()
                    self.json.saveToFile()
                    return
                elif key == 'ctrl w':
                    self.json.saveToFile()
                    msg = "  Saved \""+self.json.getFilename()+"\"  "
                    msgwidget = urwid.Text(('footerstatusactive', msg), align='center')
                    footerstatus = self.getFooterStatusWidget(msgwidget)
                    footerhelp = self.getFooterHelpWidget()
                    self.view.set_footer(urwid.Pile( [footerstatus, footerhelp] ))
                else:
                    self.view.keypress( size, key )
                    
    def handleExitRequest(self):
        entryform=self
        class CallbackEdit(urwid.Edit):
            def keypress(self,(maxcol,),key):
                if key == 'y':
                    entryform.handleSave()
                    msg = "Saved "+entryform.json.getFilename() + "\n"
                    entryform.appendEndStatusMessage(msg)
                    entryform.handleExit()
                elif key == 'n':
                    entryform.handleExit()
                elif key == 'esc':
                    entryform.cleanupExitRequest()
        prompt=CallbackEdit('Save changes (ANSWERING "No" WILL DESTROY CHANGES) ? ', "")
        self.view.set_focus("footer")
        helptext =  [("Y","Yes"),("N","No"),("ESC","Cancel")]
        footerstatus = self.getFooterStatusWidget(prompt, active=True)
        footerhelp = self.getFooterHelpWidget(helptext=helptext)
        self.view.set_footer(urwid.Pile( [footerstatus, footerhelp] ))

    def handleSave(self):
        self.json.saveToFile()

    def handleExit(self):
        raise JsonWidgetExit()

    def cleanupExitRequest(self):
        self.view.set_focus("body")
        footerstatus = self.getFooterStatusWidget()
        footerhelp = self.getFooterHelpWidget()
        self.view.set_footer(urwid.Pile( [footerstatus, footerhelp] ))

    def appendEndStatusMessage(self, status):
        self.endstatusmessage += status
        
    def getEndStatusMessage(self):
        return self.endstatusmessage
        

