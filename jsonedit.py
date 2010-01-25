#!/usr/bin/python

import json
import urwid.curses_display
import urwid

class SchemaNode:
    def __init__(self, key, data, parent=None):
        # data loaded from the schema
        self.data=data
        # key for the parent
        self.parent=parent
        # global index for the node
        self.key=key
        if self.parent==None:
            self.depth=0
        else:
            self.depth=self.parent.getDepth()+1
        if(self.data['type']=='map'):
            self.children = []
            for subkey, subnode in self.data['mapping'].items():
                self.children.append( SchemaNode(subkey, subnode, parent=self) )

    def showNode(self):
        if(self.getType()=='map'):
            print self.getTitle() + ":"
            for child in self.getChildren():
                child.showNode()
        if(self.getType()=='str'):
            print self.indent() + self.getTitle() + ":"

    def getDepth(self):
        return self.depth

    def indent(self, indentstr="    "):
        return indentstr * self.depth    
    
    def getTitle(self):
        if self.data.has_key('title'):
            return self.data['title']
        else:
            return self.key

    def getType(self):
        return self.data['type']
        
    def getChildren(self):
        return self.children

class EntryForm:
    def __init__(self, schema):
        self.ui = urwid.curses_display.Screen()
        self.ui.register_palette( [ ('default', 'default', 'default'), 
                                    ('editfield', 'light gray', 'dark blue'),
                                    ('editfieldfocus', 'white', 'dark red') ] )
        self.schema = schema

    def getFormArray(self, schemaNode=None):
        if(schemaNode==None):
            schemaNode=self.schema
        formarray=[]
        if(schemaNode.getType()=='map'):
            formarray.append(urwid.Text( schemaNode.getTitle() + ": " ))
            for child in schemaNode.getChildren():                
                formarray.extend(self.getFormArray(child))
        if(schemaNode.getType()=='str'):
            editfield = urwid.Edit( ('default', schemaNode.getTitle() + ": "), "" )
            formarray.append( urwid.AttrWrap( editfield, 'editfield', 'editfieldfocus') )
        return formarray

    def run(self):
        formarray = self.getFormArray()
        print formarray
        walker = urwid.SimpleListWalker( formarray )
        listbox = urwid.ListBox( walker )
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


def show_form(schema):
    # a full schema is just a node
    schemaobj=SchemaNode('root', schema)
    schemaobj.showNode()
    form=EntryForm(schemaobj)
    form.run()

def main():
    # load the schema
    schema = json.load(open('simpleaddr-schema.json'))
    show_form(schema)

main()
