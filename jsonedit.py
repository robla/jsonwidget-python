#!/usr/bin/python

import json

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


def show_form(schema):
    # a full schema is just a node
    schemaobj=SchemaNode('root', schema)
    schemaobj.showNode()

def main():
    # load the schema
    schema = json.load(open('simpleaddr-schema.json'))
    show_form(schema)

main()
