#!/usr/bin/python

import json
import urwid.curses_display
import urwid
import optparse

class Error(RuntimeError):
    pass

# Force monochrome for now.  Will probably revisit when 0.9.9 is widely 
# deployed
urwid.curses_display.curses.has_colors = lambda : False

class SchemaNode:
    def __init__(self, key, data, parent=None):
        # data loaded from the schema
        self.data=data
        # object ref for the parent
        self.parent=parent
        # local index for the node
        self.key=key
        if self.parent==None:
            self.depth=0
            self.rootschema=self
        else:
            self.depth=self.parent.getDepth()+1
            self.rootschema=self.parent.getRootSchema()
        if(self.data['type']=='map'):
            self.children = []
            for subkey, subnode in self.data['mapping'].items():
                self.children.append( SchemaNode(subkey, subnode, parent=self) )
        elif(self.data['type']=='seq'):
            self.children = [ SchemaNode( 0, self.data['sequence'][0], parent=self) ]

    def getDepth(self):
        return self.depth
    
    def getRootSchema(self):
        return self.rootschema

    def getTitle(self):
        if self.data.has_key('title'):
            return self.data['title']
        else:
            return str(self.key)

    def getType(self):
        return self.data['type']
        
    def getChildren(self):
        return self.children
        
    # TODO: fix up self.children to be a map rather than a plain sequence
    def getChild(self, key):
        if(self.getType()=='map'):
            for item in self.children:
                if(item.getKey()==key):
                    return item
        elif(self.getType()=='seq'):
            return self.children[key]
        else:
            return None
    
    # getChildSeqSchema: Return the schema node for a child sequence 
    # (Simple detail, but abstracting because it may not be true for future
    # JSON schemas)
    def getChildSeqSchema(self):
        # first element in sequence is the schema
        return self.getChild(0)
    
    def getKey(self):
        return self.key

    def isEnum(self):
        return self.data.has_key('enum')
        
    def enumOptions(self):
        return self.data['enum']

class JsonNode:
    def __init__(self, key, data, parent=None, schemanode=None):
        # local index for the node
        self.key=key
        # data loaded from the schema
        self.data=data
        # object ref for the parent
        self.parent=parent
        if self.parent==None:
            self.depth=0
        else:
            self.depth=self.parent.getDepth()+1
        self.attachSchemaNode(schemanode)

    def attachSchemaNode(self, schemanode):
        jsontype=self.getType()
        schematype=schemanode.getType()
        
        # is the json type appropriate for the expected schema type?
        isTypeMatch = schematype=='any' or schematype==jsontype or jsontype=='none'

        if isTypeMatch:
            self.schemanode=schemanode
            if jsontype=='map':
                self.children={}
                for subkey, subnode in self.data.items():
                    subschemanode=self.schemanode.getChild(subkey)
                    if subschemanode==None:
                        raise("Validation error: %s not a valid key in %s" % (subkey, self.schemanode.getKey()))
                    self.children[subkey]=JsonNode(subkey, subnode, parent=self, schemanode=subschemanode)
            elif jsontype=='seq':
                i=0
                self.children=[]
                for subnode in self.data:
                    subschemanode=self.schemanode.getChildSeqSchema()
                    self.children.append( JsonNode(i, subnode, parent=self, schemanode=subschemanode) )
                    i+=1
        else:
            raise Error("Validation error: type mismatch - key: %s data: %s jsontype: %s schematype: %s" % (self.key, str(self.data), jsontype, schematype) )

    def getSchemaNode(self):
        return self.schemanode

    def getType(self):
        if(isinstance(self.data, basestring)):
            return 'str'
        elif(isinstance(self.data, bool)):
            return 'bool'
        elif(isinstance(self.data, int)):
            return 'int'
        elif(isinstance(self.data, float)):
            return 'number'
        elif(isinstance(self.data, dict)):
            return 'map'
        elif(isinstance(self.data, list)):
            return 'seq'
        elif(self.data==None):
            return 'none'
        else: 
            raise Error("unknown type: %s" % type(self.data).__name__)
        
    def getData(self):
        return self.data
    
    def setData(self, data):
        self.data=data
        self.parent.setChildData(self.key, data)

    def getChildren(self):
        if(isinstance(self.children, dict)):
            return self.children.values()
        elif(isinstance(self.data, list)):
            return self.children
        else:
            return None

    def setChildData(self, key, data):
        self.data[key]=data

    def isEnum(self):
        return self.data.has_key('enum')
        
    def enumOptions(self):
        return self.data['enum']

    def getDepth(self):
        return self.depth
    
    # debugging function
    def printTree(self):
        jsontype=self.getType()
        if jsontype=='map' or jsontype=='seq':
            print self.schemanode.getTitle()
            for child in self.getChildren():
                child.printTree()
        else:
            print self.schemanode.getTitle() + ": " + self.getData()
        

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


def show_form(schema, jsondata=None):
    # a full schema is just a node
    schemaobj=SchemaNode('root', schema)
    jsonobj=JsonNode('root', jsondata, schemanode=schemaobj)
    #jsonobj.printTree()
    form=EntryForm(jsonobj)
    form.run()

def main():
    usage = "usage: %prog [options] arg"
    parser = optparse.OptionParser(usage)
    parser.add_option("-s", "--schema", dest="schema",
                      default="simpleaddr-schema.json",
                      help="use this schema to build the form")
    (options, args) = parser.parse_args()
    if len(args) > 1:
        parser.error("Too many arguments.  Just one .json file at a time, please.")
    schema = json.load(open(options.schema))
    if len(args)==1:
        jsondata = json.load(open(args[0]))
    else:
        jsondata = None
    show_form(schema, jsondata=jsondata)

if __name__ == "__main__":
    main()


