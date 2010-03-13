#!/usr/bin/python
# JsonOrderMap - class for scraping key order out of JSON text
#
# Copyright (c) 2010, Rob Lanphier
# All rights reserved.
# Licensed under BSD-style license.  See LICENSE.txt for details.


import json

try:
    import simpleparse
    from simpleparse.common import strings, numbers
except ImportError:
    import sys
    msg = """
  jsonwidget.jsonorder requires simpleparse, which doesn't appear to be
  installed.  
  
  The latest version of simpleparse for all systems can be found at:
      http://simpleparse.sourceforge.net/

  ...or in easy_install as "simpleparse"

  On Debian and Ubuntu, simply install 'python-simpleparse'.

"""
    sys.stderr.writelines(msg)
    sys.exit(2)

class JsonOrderMapError(RuntimeError):
    pass


# JSON grammar to pass to simpleparse
jsonbnf = r"""
<ws>        := [ \t\n\r]*

>string_json< := string_single_quote / string_double_quote
key := string_json
array := "[", ws, ( value, (ws, ",", ws, value)* )?, ws, "]"

member := key, ws, ":", ws, value 
object := "{", ws, ( member, ( ws, ",", ws, member )* )?, ws, "}"

true  := "true"
false := "false"
null  := "null"
>value< := false / null / true / object / array / float / int / string_json
>document< := ws, value, ws
"""


class JsonOrderMap(object):
    """
    Partial JSON parser to extract key order from a JSON file.
    
    Usage:
        foo = "{'a':1,'b':1,'c':1}
        foomap = JsonOrderMap(foo).get_order_map()
        
    The return value from get_order_map holds ordered lists of keys associated
    with the JSON file (organized into a hierarchy of dicts mirroring the 
    original JSON).
    """
    def __init__(self, jsonbuffer): 
        self._buffer = jsonbuffer
        self._ordermap = {'keys':[],'children':{}}
        self._parser = simpleparse.parser.Parser(jsonbnf, 'document')
        success, results, next = self._parser.parse(jsonbuffer)
        if success:
            self._process_value(results[0], self._ordermap)
        else:
            raise JsonOrderMapError("Couldn't parse buffer")

    def _process_object(self, results, ordermap, depth=0, key=[]):
        ordermap['keys']=[]
        ordermap['children']={}
        for childtuple in results:
            type, start, end, child = childtuple
            if type == 'member':
                keytuple = child[0][3][0][3][0]
                keystart = keytuple[1]
                keyend = keytuple[2]
                newkey = self._buffer[keystart:keyend]
                ordermap['keys'].append(newkey)
                valuestart = child[1][1]
                valueend = child[1][2]
                ordermap['children'][newkey] = {}
                self._process_value(child[1], ordermap['children'][newkey], 
                                   depth=depth+1, key=key+[newkey])

    def _process_array(self, results, ordermap, depth=0, key=[]):
        ordermap['keys']=range(len(results))
        ordermap['children']={}
        for i in range(len(results)):
            ordermap['children'][i] = {}
            self._process_value(results[i], ordermap['children'][i], 
                                depth=depth+1, key=key+[i])

    def _process_value(self, results, ordermap, depth=0, key=[]):
        type, start, end, child = results
        if type == 'object':
            self._process_object(child, ordermap, depth=depth, key=key)
        elif type == 'array':
            self._process_array(child, ordermap, depth=depth, key=key)

    def get_order_map(self):
        """
        Returns an ordered lists of keys associated with the JSON file 
        (organized into a hierarchy of dicts mirroring the original JSON).
        """
        return self._ordermap

if __name__ == "__main__":
    import json
    import optparse

    usage = "usage: %prog [options] image"
    parser = optparse.OptionParser(usage)
    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error("Too many arguments.")
    if len(args) == 1:
        foo = open(args[0]).read()
    else:
        foo = "{'a':1,'b':1,'c':{'c1':1,'c2':1},'d':['e','f','g']}"

    foomap = JsonOrderMap(foo).get_order_map()
    print "Original JSON: ", foo
    print "Order map:\n", json.dumps(foomap, indent=4)
    

