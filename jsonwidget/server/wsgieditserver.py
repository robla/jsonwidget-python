#!/usr/bin/python

from wsgiref.simple_server import make_server

import jsonwidget
import os
import sys
import string

class WebResponse(object):
    def __init__(self, content_directory=None, start_response=None):
        self.content_directory = content_directory
        self.start_response = start_response

    def serve_template(self, file, vars={}, content_type='text/html'):
        status = '200 OK'
        headers = [('Content-type', content_type)]
        self.start_response(status, headers)
        buffer = open(os.path.join(self.content_directory, file), 'r').read()
        return string.Template(buffer).substitute(vars)

    def serve_file(self, file, content_type='text/plain'):
        status = '200 OK'
        headers = [('Content-type', content_type)]
        self.start_response(status, headers)

        return open(os.path.join(self.content_directory, file), 'r').read() 

    def serve_404(self):
        status = '404 Not Found'
        headers = [('Content-type', 'text/html')]
        self.start_response(status, headers)
        return "File not found"

def get_server_func(content_directory=None, jsonschema=None, jsonfile=None):
    javascript = ['json.js', 'jsonedit.js']
    css = ['jsonwidget.css']
    def start_server(environ, start_response):
        path = environ['PATH_INFO'][1:]

        response = WebResponse(content_directory=content_directory,
                               start_response=start_response)
        if path == '':
            vars = {'jsonschema':jsonschema, 'jsonfile':jsonfile}
            return response.serve_template('index.tpl', vars=vars)
        elif path in javascript:
            return response.serve_file(path, 'text/plain')
        elif path in css:
            return response.serve_file(path, 'text/plain')
        else:
            return response.serve_404()
    return start_server

jsonfile = open(sys.argv[1]).read()
jsonschema = open(sys.argv[2]).read()
server_func = get_server_func(content_directory=sys.path[0],
                              jsonschema=jsonschema,
                              jsonfile=jsonfile)

httpd = make_server('', 8000, server_func)
print "Serving on port 8000..."

httpd.serve_forever()

