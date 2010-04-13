#!/usr/bin/python

from wsgiref.simple_server import make_server

import jsonwidget
import json
import os
import sys
import string
import cgi

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

    def handle_post_response(self, environment=None, jsonfile=None, 
                             schemafile=None):
        form = cgi.FieldStorage(fp=environment['wsgi.input'], 
                                environ=environment)
        
        jsonbuffer = form.getfirst('sourcearea')
        
        success = True
        servererror = ''
        try:
            jsondata = json.loads(jsonbuffer)
        except ValueError as inst:    
            success = False
            servererror = str(inst)
        if success:
            try:
                jsonnode = jsonwidget.jsonnode.JsonNode(data=jsondata, 
                                                        schemafile=schemafile)
            except jsonwidget.jsonnode.JsonNodeError as inst:
                servererror = "Invalid JSON.  Schema: " + schemafile + "\n"
                servererror += str(inst) + "\n"
                success = False
            except Exception as inst:
                servererror = "Unknown error.  Schema: " + schemafile + "\n"
                servererror += str(inst) + "\n"
                success = False
        if success:
            try:
                jsonnode.save_to_file(jsonfile)
            except Exception as inst:
                servererror = str(inst) + "\n"
                success = False
        schemabuffer = open(schemafile).read()
        # TODO: figure out right way to sanitize jsonbuffer before sending it
        # back out.  DANGER -- this is possible source of XSS and maybe worse
        vars = {'schema':schemabuffer, 
                'json':jsonbuffer,
                'servererror':servererror}
        index = find_server_file('index.tpl')
        return self.serve_template(index, vars=vars)


def get_server_func(content_directory=None, schemafile=None, jsonfile=None):
    jsonbuffer = open(jsonfile).read()
    schemabuffer = open(schemafile).read()
    javascript = ['json.js', 'jsonedit.js']
    css = ['jsonwidget.css']
    def start_server(environ, start_response):
        path = environ['PATH_INFO'][1:]

        response = WebResponse(content_directory=content_directory,
                               start_response=start_response)
        if environ['REQUEST_METHOD'] == 'POST':
            return response.handle_post_response(environment=environ,
                                                 jsonfile=jsonfile,
                                                 schemafile=schemafile)
        elif path == '':
            vars = {'schema':schemabuffer, 
                    'json':jsonbuffer,
                    'servererror':''}
            index = find_server_file('index.tpl')
            return response.serve_template(index, vars=vars)
        elif path in javascript:
            filename = find_server_file(path)
            return response.serve_file(filename, 'text/javascript')
        elif path in css:
            filename = find_server_file(path)
            return response.serve_file(filename, 'text/css')
        else:
            return response.serve_404()
    return start_server


def start_server(jsonfile=None, schemafile=None, port=8000, noisy=True):
    server_func = get_server_func(content_directory=sys.path[0],
                                  schemafile=schemafile,
                                  jsonfile=jsonfile)

    httpd = make_server('', port, server_func)
    if noisy:
        print "Serving on port %i.  See http://localhost:%i/" % (port, port)

    httpd.serve_forever()


def find_server_file(filename):
    """
    Resolve filename to a full path.
    """
    try:
        import pkg_resources
    except ImportError:
        filename = os.path.join("jsonwidget", "server", filename)
    else:
        filename = os.path.join("server", filename)
        filename = pkg_resources.resource_filename("jsonwidget", 
            filename)
    return filename


if __name__ == "__main__":
    jsonfile = sys.argv[1]
    schemafile = sys.argv[2]

    start_server(jsonfile=jsonfile, schemafile=schemafile)

