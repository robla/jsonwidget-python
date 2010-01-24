#!/usr/bin/python

import json

class SchemaNode:
    def __init__(this, key, data, parent=None):
        # data loaded from the schema
        this.data=data
        # key for the parent
        this.parent=parent
        # global index for the node
        this.key=key
        if this.parent==None:
            this.depth=0
        else:
            this.depth=this.parent.getDepth()+1

    def showNode(this):
        if(this.data['type']=='map'):
            print this.getTitle() + ":"
            for subkey, subnode in this.data['mapping'].items():
                schemaobj=SchemaNode(subkey, subnode, parent=this)
                schemaobj.showNode()
        if(this.data['type']=='str'):
            print this.indent(),
            print this.getTitle(),
            print ": "

    def getDepth(this):
        return this.depth

    def indent(this, indentstr="    "):
        return indentstr * this.depth    
    
    def getTitle(this):
        if this.data.has_key('title'):
            return this.data['title']
        else:
            return this.key


def show_form(schema):
    # a full schema is just a node
    schemaobj=SchemaNode('root', schema)
    schemaobj.showNode()

def main():
    # load the schema
    schema = json.load(open('simpleaddr-schema.json'))
    show_form(schema)

main()
