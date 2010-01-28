#!/usr/bin/python

import json

class Error(RuntimeError):
    pass

# Each SchemaNode instance represents one node in the data tree.  Each element 
# of a child sequence (i.e. list in Python) and child map (i.e. dict in Python)
# gets its own child SchemaNode.
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

    # Set raw data
    # TODO: move to storing child data exclusively in children, because current
    # method has n log n memory footprint.
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

    # how deep is this in the tree
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

