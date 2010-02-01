#!/usr/bin/python
# Library for reading JSON files according to given JSON Schema
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.  
# Licensed under BSD-style license.  See LICENSE.txt for details.

import json
# sets deprecated in Python 2.6
import sets

class Error(RuntimeError):
    pass

# Each SchemaNode instance represents one node in the data tree.  Each element 
# of a child sequence (i.e. list in Python) and child map (i.e. dict in Python)
# gets its own child SchemaNode.
class SchemaNode:
    def __init__(self, key=None, data=None, filename=None, parent=None):
        if filename is not None:
            self.filename=filename
            if data is None:
                self.loadFromFile()
        else:
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
            self.children = {}
            for subkey, subdata in self.data['mapping'].items():
                self.children[subkey]=SchemaNode(key=subkey, data=subdata, 
                                                 parent=self)
        elif(self.data['type']=='seq'):
            self.children = [ SchemaNode(key=0, data=self.data['sequence'][0], 
                                         parent=self) ]

    def loadFromFile(self, filename=None):
        if filename is not None:
            self.filename=file
        self.data=json.load(open(self.filename))

    def getDepth(self):
        return self.depth
    
    def getRootSchema(self):
        return self.rootschema

    def getTitle(self):
        if self.data.has_key('title'):
            return self.data['title']
        else:
            if self.depth>0 and self.parent.getType()=='seq':
                return self.parent.getTitle()
            else:
                return str(self.key)

    def getType(self):
        return self.data['type']
        
    # get a list of children, possibly ordered
    # Note that even though the JSON spec says maps are unordered, it's pretty
    # rude to muck with someone else's content ordering in a text file, and ad 
    # hoc forms benefit greatly from being able to control the order of elements
    def getChildren(self):
        if(isinstance(self.children, dict)):
            return self.children.values()
        elif(isinstance(self.children, list)):
            return self.children
        else:
            raise Error("self.children has invalid type %s" % type(self.children).__name__)
        
    def getChild(self, key):
        type=self.getType()
        if(type=='map'):
            return self.children[key]
        elif(type=='seq'):
            return self.children[0]
        else:
            raise Error("self.children has invalid type %s" % type)

    def getChildKeys(self):
        return self.children.keys()
    
    def getKey(self):
        return self.key

    def isEnum(self):
        return self.data.has_key('enum')
        
    def enumOptions(self):
        return self.data['enum']

    def getBlankValue(self):
        type=self.getType()
        if(type=='map'):
            retval={}
        elif(type=='seq'):
            retval=[]
        elif(type=='int' or type=='number'):
            retval=0
        elif(type=='bool'):
            retval=False
        elif(type=='str'):
            retval=""
        else:
            retval=None
        return retval


# JsonNode is a class to store the data associated with a schema.  Each node
# of the tree gets tied to a SchemaNode
class JsonNode:
    def __init__(self, key=None, parent=None, filename=None, data=None,
                 schemanode=None, schemadata=None, schemafile=None):
        if filename is not None:
            self.filename=filename
            if data is None:
                self.loadFromFile()
        else:
            self.data=data           

        if schemanode is not None:
            self.schemanode=schemanode
        else:
            schemanode=SchemaNode(key=key, data=schemadata, 
                                  filename=schemafile)

        # local index for the node
        self.key=key
        # object ref for the parent
        self.parent=parent
        # self.children will get set in attachSchemaNode if there are any
        self.children=[]
        if self.parent==None:
            self.depth=0
        else:
            self.depth=self.parent.getDepth()+1
        if not self.isTypeMatch(schemanode):
            raise Error("Validation error: type mismatch - key: %s data: %s jsontype: %s schematype: %s" % (self.key, str(self.data), jsontype, schematype) )
        else:
            self.attachSchemaNode(schemanode)

    def loadFromFile(self, filename=None):
        if filename is not None:
            self.filename=filename
        self.data=json.load(open(self.filename))

    # pair this data node to the corresponding part of the schema
    def isTypeMatch(self, schemanode):
        jsontype=self.getType()
        schematype=schemanode.getType()

        # is the json type appropriate for the expected schema type?
        isTypeMatch = (schematype=='any' or 
                       schematype==jsontype or 
                       jsontype=='none' or
                       (jsontype=='int' and schematype=='number'))


        return isTypeMatch

    # pair this data node to the corresponding part of the schema
    def attachSchemaNode(self, schemanode):
        self.schemanode=schemanode

        jsontype=self.getType()
        schematype=schemanode.getType()
        if schematype=='map':
            self.children={}
        elif schematype=='seq':
            self.children=[]
        if jsontype=='map':
            for subkey, subdata in self.data.items():
                subschemanode=self.schemanode.getChild(subkey)
                if subschemanode==None:
                    raise("Validation error: %s not a valid key in %s" % (subkey, self.schemanode.getKey()))
                self.children[subkey]=JsonNode(key=subkey, data=subdata, 
                                               parent=self, schemanode=subschemanode)
        elif jsontype=='seq':
            i=0
            for subdata in self.data:
                subschemanode=self.schemanode.getChild(i)
                self.children.append(JsonNode(key=i, data=subdata, parent=self, 
                                              schemanode=subschemanode))
                i+=1

    def getSchemaNode(self):
        return self.schemanode

    # get type string as defined by the schema language
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

    def getKey(self):
        return self.key

    def getData(self):
        return self.data

    # Set raw data
    # TODO: move to storing child data exclusively in children, because current
    # method has n log n memory footprint.
    def setData(self, data):
        self.data=data
        if(self.depth>0):
            self.parent.setChildData(self.key, data)

    # get a list of children, possibly ordered
    # Note that even though the JSON spec says maps are unordered, it's pretty
    # rude to muck with someone else's content ordering in a text file, and ad 
    # hoc forms benefit greatly from being able to control the order of elements
    def getChildren(self):
        if(isinstance(self.children, dict)):
            return self.children.values()
        elif(isinstance(self.children, list)):
            return self.children
        else:
            raise Error("self.children has invalid type %s" % type(self.children).__name__)

    def getChildKeys(self):
        return self.children.keys()
    
    # this function returns the list of keys that don't yet have 
    # associated json child nodes associated with them
    def getAvailableKeys(self):
        if(self.schemanode.getType()=='map'):
            schemakeys=sets.Set(self.schemanode.getChildKeys())
            jsonkeys=sets.Set(self.getChildKeys())
            unusedkeys=schemakeys.difference(jsonkeys)
            return list(unusedkeys)
        elif(self.schemanode.getType()=='seq'):
            return [ len(self.children) ]
        else:
            raise Error("type %s not implemented" % self.getType())

    def setChildData(self, key, data):
        if(self.data==None):
            type=self.schemanode.getType()
            self.data=self.schemanode.getBlankValue()
        if(self.getType()=='seq' and key==len(self.data)):
            self.data.append(data)
        else:
            self.data[key]=data

    def addChild(self, key=None):
        schemanode=self.schemanode.getChild(key)
        newnode=JsonNode(key=key, data=schemanode.getBlankValue(), parent=self, 
                         schemanode=schemanode)
        self.setChildData(key, newnode.getData())
        if(self.getType()=='seq'):
            self.children.insert(key, newnode)
        else:
            self.children[key]=newnode

    def isEnum(self):
        return self.data.has_key('enum')

    def enumOptions(self):
        return self.data['enum']

    # how deep is this node in the tree?
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

    def getTitle(self):
        schematitle=self.schemanode.getTitle()
        if(self.depth>0 and self.parent.schemanode.getType()=='seq'):
            title="%s #%i" % (schematitle, self.getKey()+1)
        else:
            title=schematitle
        return title
        
    def getChildTitle(self, key):
        childschema=self.schemanode.getChild(key)
        schematitle=childschema.getTitle()
        if(self.schemanode.getType()=='seq'):
            title="%s #%i" % (schematitle, key+1)
        else:
            title=schematitle
        return title


