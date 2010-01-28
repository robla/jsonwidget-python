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


class MapEditWidget( urwid.WidgetWrap ):
    def __init__(self, schemanode, jsonnode=None):
        maparray=[]
        maparray.append(urwid.Text( schemanode.getTitle() + ": " ))
        leftmargin = urwid.Text( "" )
        pilearray=[]

        if(jsonnode==None):
            raise Error("jsonnode not really optional")
        for child in jsonnode.getChildren():
            pilearray.append(get_schema_widget(child))
        mapfields = urwid.Pile( pilearray )
        maparray.append(urwid.Columns( [ ('fixed', 2, leftmargin), mapfields ] ))
        urwid.WidgetWrap.__init__(self, urwid.Pile(maparray))

class SeqEditWidget( urwid.WidgetWrap ):
    def __init__(self, schemanode, jsonnode=None):
        maparray=[]
        maparray.append(urwid.Text( schemanode.getTitle() + ": " ))
        leftmargin = urwid.Text( "" )
        pilearray=[]
        if(jsonnode==None):
            raise Error("jsonnode not really optional")
        for child in jsonnode.getChildren():                
            pilearray.append(get_schema_widget(child))
        mapfields = urwid.Pile( pilearray )
        maparray.append(urwid.Columns( [ ('fixed', 2, leftmargin), mapfields ] ))
        urwid.WidgetWrap.__init__(self, urwid.Pile(maparray))

class GenericEditWidget( urwid.WidgetWrap ):
    def __init__(self, schemanode, jsonnode=None):
        self.schema = schemanode
        self.json = jsonnode
        editcaption = urwid.Text( ('default', schemanode.getTitle() + ": ") )
        editfieldwidget = self.getEditFieldWidget()
        editfield = self.wrapEditFieldWidget(editfieldwidget)
        editpair = urwid.Columns ( [ ('fixed', 20, editcaption), editfield ] )
        urwid.WidgetWrap.__init__(self, editpair)

    def getEditFieldWidget(self):
        thiswidget=self
        class CallbackEdit(urwid.Edit):
            def set_edit_text(self, text):
                urwid.Edit.set_edit_text(self, text)
                thiswidget.json.setData(text)
        return CallbackEdit("", str(self.json.getData()))
        
    def wrapEditFieldWidget(self, fieldwidget):
        return urwid.AttrWrap(fieldwidget, 'editfield', 'editfieldfocus')

class IntEditWidget( GenericEditWidget ):
    def getEditFieldWidget(self):
        return urwid.IntEdit("", self.json.getData())

class BoolEditWidget( GenericEditWidget ):
    def getEditFieldWidget(self):
        return urwid.CheckBox("", self.json.getData())
    def wrapEditFieldWidget(self, fieldwidget):
        return fieldwidget
        
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
    def wrapEditFieldWidget(self, fieldwidget):
        return fieldwidget

class EntryForm:
    def __init__(self, json):
        self.ui = urwid.curses_display.Screen()
        self.ui.register_palette( [ ('default', 'default', 'default'), 
                                    ('editfield', 'light gray', 'dark blue', 'underline'),
                                    ('editfieldfocus', 'white', 'dark red', 'underline') ] )
        #('editfield', 'light gray', 'dark blue', 'underline')
        self.json = json
        self.schema = json.getSchemaNode()

    def run(self):
        widget = get_schema_widget(self.json)
        self.walker = urwid.SimpleListWalker( [ widget ] )
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
                keys = self.ui.get_input()
            for key in keys:
                if key == 'window resize':
                    size = self.ui.get_cols_rows()
                elif key == 'ctrl x':
                    print "Exiting by ctrl-x"
                    return
                else:
                    self.view.keypress( size, key )

