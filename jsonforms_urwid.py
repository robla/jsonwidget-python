#!/usr/bin/python

# Library for building urwid-based forms from JSON schemas

from jsonschema import *

class Error(RuntimeError):
    pass

import json
import urwid.curses_display
import urwid

# Class factory for UI widgets.
# node: either a SchemaNode or JsonNode
# returns the appropriate UI widget
def get_schema_widget( node ):
    if(isinstance(node, JsonNode)):
        schemanode=node.getSchemaNode()
        jsonnode=node
    else:
        raise Error("Type error: %s" % type(node).__name__) 

    if(schemanode.getType()=='map'):
        return MapEditWidget(schemanode, jsonnode=jsonnode)
    elif(schemanode.getType()=='seq'):
        return SeqEditWidget(schemanode, jsonnode=jsonnode)
    elif(schemanode.getType()=='str'):
        if(schemanode.isEnum()):
            return EnumEditWidget(schemanode, jsonnode=jsonnode)
        else:
            return GenericEditWidget(schemanode, jsonnode=jsonnode)
    elif(schemanode.getType()=='int'):
        return IntEditWidget(schemanode, jsonnode=jsonnode)
    elif(schemanode.getType()=='bool'):
        return BoolEditWidget(schemanode, jsonnode=jsonnode)
    else:
        return GenericEditWidget(schemanode, jsonnode=jsonnode)

# Series of editing widgets follows, each appropriate to a datatype or two

# Map/dict edit widget/container
class MapEditWidget( urwid.WidgetWrap ):
    def __init__(self, schemanode, jsonnode=None):
        self.schema = schemanode
        self.json = jsonnode
        maparray=[]
        maparray.append(urwid.Text( schemanode.getTitle() + ": " ))
        leftmargin = urwid.Text( "" )
        # build a vertically stacked array of widgets
        pilearray=[]

        if(jsonnode==None):
            raise Error("jsonnode not really optional")
        for child in jsonnode.getChildren():
            pilearray.append(get_schema_widget(child))
        pilearray.append(FieldAddButtons(self, self.json.getUnusedSchemaNodes()))
        mapfields = urwid.Pile( pilearray )
        maparray.append(urwid.Columns( [ ('fixed', 2, leftmargin), mapfields ] ))
        urwid.WidgetWrap.__init__(self, urwid.Pile(maparray))

    def addNode(self, schemanode):
        newnode=JsonNode(schemanode.getKey(), "", parent=self.json, schemanode=schemanode)
        newwidget=get_schema_widget(newnode)
        # This doesn't work
        #self.w.widget_list.append(newwidget)

# Seq/list edit widget/container
class SeqEditWidget( urwid.WidgetWrap ):
    def __init__(self, schemanode, jsonnode=None):
        self.schema = schemanode
        self.json = jsonnode
        maparray=[]
        maparray.append(urwid.Text( schemanode.getTitle() + ": " ))
        leftmargin = urwid.Text( "" )
        # build a vertically stacked array of widgets
        pilearray=[]
        if(jsonnode==None):
            raise Error("jsonnode not really optional")
        for child in jsonnode.getChildren():                
            pilearray.append(get_schema_widget(child))
        mapfields = urwid.Pile( pilearray )
        maparray.append(urwid.Columns( [ ('fixed', 2, leftmargin), mapfields ] ))
        urwid.WidgetWrap.__init__(self, urwid.Pile(maparray))

# generic widget used for free text entry (e.g. strings)
class GenericEditWidget( urwid.WidgetWrap ):
    def __init__(self, schemanode, jsonnode=None):
        self.schema = schemanode
        self.json = jsonnode
        editcaption = urwid.Text( ('default', schemanode.getTitle() + ": ") )
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
    def __init__(self, parentwidget, nodelist):
        self.parentwidget = parentwidget
        self.nodelist = nodelist
        caption = urwid.Text( ('default', "Add fields: ") )
        buttonfield = self.getButtons()
        editpair = urwid.Columns ( [ ('fixed', 20, caption), buttonfield ] )
        urwid.WidgetWrap.__init__(self, editpair)

    def getButtons(self):
        #TODO: wire this up
        parentwidget=self.parentwidget
        #TODO: fix this
        if(len(self.nodelist)>0):
            node=self.nodelist[0]
        else:
            node=None
        def foo(stuff):
            parentwidget.addNode(node)

        buttons=[]
        for node in self.nodelist:
            fieldname = node.getTitle()
            buttons.append(urwid.Button(fieldname,foo))
        #TODO: remove hard coded widths
        return urwid.GridFlow( buttons, 13,3,1, 'left')

# the top-level form where all of the widgets get placed.
# I'm guessing this should get replaced with a MainLoop when this moves to urwid
# 0.99.
class EntryForm:
    def __init__(self, json):
        self.ui = urwid.curses_display.Screen()
        self.ui.register_palette( [ ('default', 'default', 'default'), 
                                    ('editfield', 'light gray', 'dark blue', 'underline'),
                                    ('editfieldfocus', 'white', 'dark red', 'underline') ] )
        self.json = json
        self.schema = json.getSchemaNode()

    def run(self):
        widget = get_schema_widget(self.json)
        def foo(stuff):
            pass
        editcaption = urwid.Text( ('default', "") )
        morebutton = urwid.Button("more and bigger and stuff",foo)
        morebuttonpair = urwid.Columns ( [ ('fixed', 20, editcaption), morebutton ] )
        self.walker = urwid.SimpleListWalker( [ widget,morebutton ] )
        listbox = urwid.ListBox( self.walker )
        self.view = urwid.Frame( listbox )

        self.ui.run_wrapper( self.runLoop )

    def runLoop(self):
        size = self.ui.get_cols_rows()
        while(True):
            canvas = self.view.render( size, focus=1 )
            self.ui.draw_screen( size, canvas )
            keys = None
            while(keys == None):
                # self.ui.get_input() blocks for max_wait time, default 0.5 sec
                # use self.ui.set_input_timeouts() to change the default
                keys = self.ui.get_input()
            for key in keys:
                if key == 'window resize':
                    size = self.ui.get_cols_rows()
                elif key == 'ctrl x':
                    print "Exiting by ctrl-x"
                    return
                else:
                    self.view.keypress( size, key )

