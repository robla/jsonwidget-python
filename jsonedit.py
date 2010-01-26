#!/usr/bin/python

import json
import urwid.curses_display
import urwid
import optparse

# Force monochrome for now.  Will probably revisit when 0.9.9 is widely 
# deployed
urwid.curses_display.curses.has_colors = lambda : False

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
        elif(self.data['type']=='seq'):
            self.children = [ SchemaNode('0', self.data['sequence'][0], parent=self) ]

    def getDepth(self):
        return self.depth
    
    def getTitle(self):
        if self.data.has_key('title'):
            return self.data['title']
        else:
            return self.key

    def getType(self):
        return self.data['type']
        
    def getChildren(self):
        return self.children
    
    def isEnum(self):
        return self.data.has_key('enum')
        
    def enumOptions(self):
        return self.data['enum']

def get_schema_widget( schemaNode ):
    if(schemaNode.getType()=='map'):
        return MapEditWidget(schemaNode)
    elif(schemaNode.getType()=='seq'):
        return SeqEditWidget(schemaNode)
    elif(schemaNode.getType()=='str'):
        if(schemaNode.isEnum()):
            return EnumEditWidget(schemaNode)
        else:
            return GenericEditWidget(schemaNode)
    elif(schemaNode.getType()=='int'):
        return IntEditWidget(schemaNode)
    elif(schemaNode.getType()=='bool'):
        return BoolEditWidget(schemaNode)
    else:
        return GenericEditWidget(schemaNode)


class MapEditWidget( urwid.WidgetWrap ):
    def __init__(self, schemaNode):
        maparray=[]
        maparray.append(urwid.Text( schemaNode.getTitle() + ": " ))
        leftmargin = urwid.Text( "" )
        pilearray=[]
        for child in schemaNode.getChildren():                
            pilearray.append(get_schema_widget(child))
        mapfields = urwid.Pile( pilearray )
        maparray.append(urwid.Columns( [ ('fixed', 2, leftmargin), mapfields ] ))
        urwid.WidgetWrap.__init__(self, urwid.Pile(maparray))

class SeqEditWidget( urwid.WidgetWrap ):
    def __init__(self, schemaNode):
        maparray=[]
        maparray.append(urwid.Text( schemaNode.getTitle() + ": " ))
        leftmargin = urwid.Text( "" )
        pilearray=[]
        for child in schemaNode.getChildren():                
            pilearray.append(get_schema_widget(child))
        mapfields = urwid.Pile( pilearray )
        maparray.append(urwid.Columns( [ ('fixed', 2, leftmargin), mapfields ] ))
        urwid.WidgetWrap.__init__(self, urwid.Pile(maparray))

class GenericEditWidget( urwid.WidgetWrap ):
    def __init__(self, schemaNode):
        self.schema = schemaNode
        editcaption = urwid.Text( ('default', schemaNode.getTitle() + ": ") )
        editfieldwidget = self.getEditFieldWidget()
        editfield = self.wrapEditFieldWidget(editfieldwidget)
        editpair = urwid.Columns ( [ ('fixed', 20, editcaption), editfield ] )
        urwid.WidgetWrap.__init__(self, editpair)

    def getEditFieldWidget(self):
        return urwid.Edit()
        
    def wrapEditFieldWidget(self, fieldwidget):
        return urwid.AttrWrap(fieldwidget, 'editfield', 'editfieldfocus')

class IntEditWidget( GenericEditWidget ):
    def getEditFieldWidget(self):
        return urwid.IntEdit()

class BoolEditWidget( GenericEditWidget ):
    def getEditFieldWidget(self):
        return urwid.CheckBox("")
    def wrapEditFieldWidget(self, fieldwidget):
        return fieldwidget
        
class EnumEditWidget( GenericEditWidget ):
    def getEditFieldWidget(self):
        options=[]
        self.radiolist = []
        for option in self.schema.enumOptions():
            options.append(urwid.RadioButton(self.radiolist, option))
        return urwid.GridFlow( options, 13,3,1, 'left')
    def wrapEditFieldWidget(self, fieldwidget):
        return fieldwidget


class EntryForm:
    def __init__(self, schema):
        self.ui = urwid.curses_display.Screen()
        self.ui.register_palette( [ ('default', 'default', 'default'), 
                                    ('editfield', 'light gray', 'dark blue', 'underline'),
                                    ('editfieldfocus', 'white', 'dark red', 'underline') ] )
        #('editfield', 'light gray', 'dark blue', 'underline')
        self.schema = schema

    def run(self):
        widget = get_schema_widget(self.schema)
        walker = urwid.SimpleListWalker( [ widget ] )
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
    form=EntryForm(schemaobj)
    form.run()

def main():
    usage = "usage: %prog [options] arg"
    parser = optparse.OptionParser(usage)
    parser.add_option("-s", "--schema", dest="schema",
                      default="simpleaddr-schema.json",
                      help="use this schema to build the form")
    (options, args) = parser.parse_args()
    if len(args) != 0:
        parser.error("No arguments please.  Arguments are down the hall, to the right.")
    schema = json.load(open(options.schema))
    show_form(schema)

if __name__ == "__main__":
    main()


