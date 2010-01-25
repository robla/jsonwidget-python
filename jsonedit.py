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

    def showNode(self):
        if(self.data['type']=='map'):
            print self.getTitle() + ":"
            for subkey, subnode in self.data['mapping'].items():
                schemaobj=SchemaNode(subkey, subnode, parent=self)
                schemaobj.showNode()
        if(self.data['type']=='str'):
            print self.indent(),
            print self.getTitle(),
            print ": "

    def getDepth(self):
        return self.depth

    def indent(self, indentstr="    "):
        return indentstr * self.depth    
    
    def getTitle(self):
        if self.data.has_key('title'):
            return self.data['title']
        else:
            return self.key


class EntryForm:
	
    def __init__(self):
        self.ui = urwid.curses_display.Screen()
        self.ui.register_palette( [ ('default', 'default', 'default'), 
                                    ('editfield', 'light gray', 'black'),
                                    ('editfieldfocus', 'white', 'black') ] )

    def run(self):
        editfield1 = urwid.Edit( ('default', "Edit me: "), "blah blah blah" )
        editfield2 = urwid.Edit( ('default', "Edit me2: "), "blah blah blah2" )
        formarray = [ urwid.AttrWrap( editfield1, 'editfield', 'editfieldfocus'),
                      urwid.AttrWrap( editfield2, 'editfield', 'editfieldfocus') ]
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
    form=EntryForm()
    form.run()

def main():
    # load the schema
    schema = json.load(open('simpleaddr-schema.json'))
    show_form(schema)

main()
