__VERSION__ = "0.0.0"

import os
import sys
import sublime
import sublime_plugin
import threading
import webbrowser
import posixpath
import socket
import cgi
import shutil
import mimetypes
import time
import io
import subprocess

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn, TCPServer
import urllib


settings = None
thread = None
dic = None
loaded = False


def load_settings():
    defaultFisArg = ""
    defaultFisOutput = ""
    defaultfisproject = ""
    defaultPort = 8080
    defaultMimeTypes = {
        '': 'application/octet-stream',  # Default
        '.css' : 'text/css',
        '.tpl' : 'text/html',
        '.js' : 'text/javascript',
        '.jsx' : 'text/javascript',
        '.php' : 'text/html',
        '.asp' : 'text/html',
        '.jsp' : 'text/jsp',
        '.txt' : 'text/plain',
        '.json' : 'application/json',
        '.xml' : 'text/xml',
        '.htm' : 'text/html',
        '.text' : 'text/plain',
        '.md' : 'text/plain',
        '.xhtml' : 'text/html',
        '.html' : 'text/html',
        '.conf' : 'text/plain',
        '.po' : 'text/plain',
        '.config' : 'text/plain',
        '.coffee' : 'text/javascript',
        '.less' : 'text/css',
        '.sass' : 'text/css',
        '.scss' : 'text/css',
        '.styl' : 'text/css',
        '.manifest' : 'text/cache-manifest',
        '.svg' : 'image/svg+xml',
        '.tif' : 'image/tiff',
        '.tiff' : 'image/tiff',
        '.wbmp' : 'image/vnd.wap.wbmp',
        '.webp' : 'image/webp',
        '.png' : 'image/png',
        '.bmp' : 'image/bmp',
        '.fax' : 'image/fax',
        '.gif' : 'image/gif',
        '.ico' : 'image/x-icon',
        '.jfif' : 'image/jpeg',
        '.jpg' : 'image/jpeg',
        '.jpe' : 'image/jpeg',
        '.jpeg' : 'image/jpeg',
        '.eot' : 'application/vnd.ms-fontobject',
        '.woff' : 'application/font-woff',
        '.ttf' : 'application/octet-stream',
        '.cur' : 'application/octet-stream'
    }
    


    s = sublime.load_settings('FisComplieServer.sublime-settings')

    
    if not s.has('port'):
        s.set('port', defaultPort)
    if not s.has('fisarg'):
        s.set('fisarg', defaultFisArg)
    if not s.has('fisoutputdir'):
        s.set('fisoutputdir', defaultFisOutput)
    if not s.has("fisproject"):
        s.set('fisproject', defaultfisproject)
    if not s.has('mimetypes'):
        s.set('mimetypes', defaultMimeTypes)

    sublime.save_settings('FisComplieServer.sublime-settings')

    # Merge project and user settings.
    window = sublime.active_window()
    if window:
        view = window.active_view()
        if view:
            settings = view.settings()
            if settings:
                serverSettings = settings.get('FisComplieServer')
                if serverSettings:
                    for setting in serverSettings:
                        s.set(setting, serverSettings.get(setting))
    return s


class FisComplieServerHandler(BaseHTTPRequestHandler):

    extensions_map = {}
    defaultExtension = None
    base_path = None

    def version_string(self):
        '''overwrite HTTP server's version string'''
        return 'FisComplieServer/%s Sublime/%s' % (__VERSION__, sublime.version())


    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def send_head(self):
        path = self.translate_path(self.path)
        f = None
        if path is None:
            self.send_error(404, "File not found")
            return None
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)

        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        try:
            self.send_response(200)
            self.send_header("Content-type", ctype)
            fs = os.fstat(f.fileno())
            self.send_header("Content-Length", str(fs[6]))
            self.send_header(
                "Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise
    def guess_type(self, path):
        try:
            base, ext = posixpath.splitext(path)
            if ext in FisComplieServerHandler.extensions_map:
                return FisComplieServerHandler.extensions_map[ext]
            ext = ext.lower()
            if ext in FisComplieServerHandler.extensions_map:
                return FisComplieServerHandler.extensions_map[ext]
            else:
                return FisComplieServerHandler.extensions_map['']
        except:
            return "text/plain"

    def list_directory(self, path):
        global dic
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(403, "Access Denied")
            return None
        list.sort(key=lambda a: a.lower())
        
        r = []
        displaypath = cgi.escape(urllib.unquote(self.path))

        enc="UTF-8"
        r.append('<!DOCTYPE html>')
        r.append('<html>\n<head>\n<meta charset="%s"/>\n' % enc)
        r.append('<title>Fis Server %s</title>\n</head>\n<body>\n' % displaypath)
        r.append('<hr>\n<ul>\n')

      
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
            
            r.append('<li><a href="%s">%s</a>\n' % (linkname, displayname))

  
        r.append("</ul>\n<hr>\n</body>\n</html>\n")
        encoded = ''.join(r).encode(enc)
        
        try:
            f = io.BytesIO()
            f.write(encoded)
            f.seek(0)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=%s" % enc)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
        except error, arg:
            (errno, err_msg) = arg
            msg = "list server : {0}, errno={1}"
            msg.format(err_msg, errno)
            sublime.message_dialog(msg)
       
        return f

    def translate_path(self, path):
        global dic

        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        if FisComplieServerHandler.base_path:
            path = FisComplieServerHandler.base_path + path
        return path

    def copyfile(self, source, outputfile):
        shutil.copyfileobj(source, outputfile)

    


class FisComplieServerThreadMixIn(ThreadingMixIn, TCPServer):
    pass


class FisComplieServerThread(threading.Thread):
    httpd = None

    def __init__(self):
        settings = load_settings()
        super(FisComplieServerThread, self).__init__()
        if not mimetypes.inited:
            mimetypes.init()  # try to read system mime.types
        FisComplieServerHandler.extensions_map = mimetypes.types_map.copy()
        FisComplieServerHandler.extensions_map.update(settings.get('mimetypes'))
        FisComplieServerHandler.base_path = settings.get('fisoutputdir')
        FisComplieServerHandler.defaultExtension = settings.get('defaultExtension')
        self.httpd = FisComplieServerThreadMixIn(('', settings.get('port')), FisComplieServerHandler)
        self.setName(self.__class__.__name__)

    def run(self):
        self.httpd.serve_forever()
        self._stop = threading.Event()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self._stop.set()


class FiscomplieserverStartCommand(sublime_plugin.ApplicationCommand):
    def run(self):

        global settings, thread, dic, attempts
        settings = load_settings()
       

        os.chdir(settings.get("fisproject"))

        self.start_fis()
        # stop fis server
        if thread is not None and thread.is_alive():
            thread.stop()
            thread.join()
            thread = None
        try:
            thread = FisComplieServerThread()
            thread.start()
            self.browser_fis()
        except socket.error, arg:
            (errno, err_msg) = arg
            msg = "start server : {0}, errno={1}"
            msg.format(err_msg, errno)
            sublime.message_dialog(msg)

    def start_fis(self):
        re = os.system(settings.get('fisarg'))

    def browser_fis(self):
        url = "http://localhost:{0}/"
        url = url.format(settings.get('port'))
        webbrowser.open(url)


settings = load_settings()

def plugin_loaded():
    global settings
    settings = load_settings()

threads = threading.enumerate()
for t in threads:
    if t.__class__.__name__ is FisComplieServerThread.__name__:
        thread = t
        break
