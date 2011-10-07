"""
  Copyright notice
  ================
  
  Copyright (C) 2011
      Roberto Paleari     <roberto.paleari@gmail.com>
      Alessandro Reina    <alessandro.reina@gmail.com>
  
  This program is free software: you can redistribute it and/or modify it under
  the terms of the GNU General Public License as published by the Free Software
  Foundation, either version 3 of the License, or (at your option) any later
  version.
  
  HyperDbg is distributed in the hope that it will be useful, but WITHOUT ANY
  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
  A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License along with
  this program. If not, see <http://www.gnu.org/licenses/>.
  
"""

import SocketServer
import BaseHTTPServer
import socket
import threading
import httplib
import time
import os
import urllib
import ssl
import copy

from history import *
from http import *
from https import *
from logger import Logger

proxystate = None

class ProxyHandler(SocketServer.StreamRequestHandler):

    def __init__(self, request, client_address, server):
        self.peer = None
        self.rdata = None
        SocketServer.StreamRequestHandler.__init__(self, request, client_address, server)

    def setup(self):
        if not(self.peer):
            SocketServer.StreamRequestHandler.setup(self)
            self.rdata = self.rfile
            return

    def finish(self):
        # close SSL connection
        if self.peer:
            self.peer.close()
            self.rdata.close()

        SocketServer.StreamRequestHandler.finish(self)
        
    def createConnection(self, host, port):
        global proxystatus
        # If a SSL tunnel was established, create a HTTPS connection to the server
        if self.peer:
            try:
                conn = httplib.HTTPSConnection(host, port)
                return conn
            except HTTPException as e:
                proxystatus.log.debug(e.__str__())

        # HTTP conneciton
        return httplib.HTTPConnection(host, port)

    def sendResponse(self, res):
        # If a SSL tunnel was established, send the response through it
        if self.peer:
            self.peer.write(res)
        else:
            self.wfile.write(res)
     
    def handle(self):
        global proxystate
        
        try:
            req = HTTPRequest.build(self.rdata)
        except Exception as e:
            proxystate.log.debug("Error on reading request message")
            return
        
        # Delegate request to plugin
        req = ProxyPlugin.delegate(ProxyPlugin.EVENT_MANGLE_REQUEST, req.clone())

        # Target server host and port
        host, port = ProxyState.getTargetHost(req)
        
        if req.getMethod() == HTTPRequest.METHOD_GET:
            res = self.doGET(host, port, req)
            self.sendResponse(res)
        elif req.getMethod() == HTTPRequest.METHOD_POST:
            res = self.doPOST(host, port, req)
            self.sendResponse(res)
        elif req.getMethod() == HTTPRequest.METHOD_CONNECT:
            res = self.doCONNECT(host, port, req)

    def doGET(self, host, port, req):
        conn = self.createConnection(host, port)
        conn.request("GET", req.getPath(), '', req.headers)

        res = self._getresponse(conn)

        # Delegate response to plugin
        res = ProxyPlugin.delegate(ProxyPlugin.EVENT_MANGLE_RESPONSE, res.clone())

        data = res.serialize()
        return data

    def doPOST(self, host, port, req):
        conn = self.createConnection(host, port)
        params = urllib.urlencode(req.getParams())
        conn.request("POST", req.getPath(), params, req.headers)

        res = self._getresponse(conn)

        # Delegate response to plugin
        res = ProxyPlugin.delegate(ProxyPlugin.EVENT_MANGLE_RESPONSE, res.clone())

        data = res.serialize()
        return data

    def doCONNECT(self, host, port, req):
        global proxystate

        socket = self.request
        socket_ssl = ssl.wrap_socket(socket, server_side = True, certfile = './cert/cert.pem', ssl_version = ssl.PROTOCOL_SSLv23, do_handshake_on_connect = False)
        self.peer = socket_ssl
        HTTPSRequest.sendAck(socket)
        
        host, port = socket.getpeername()
        proxystate.log.debug("Send ack to the peer %s on port %d for establishing SSL tunnel" % (host, port))

        while True:
            try:
                socket_ssl.do_handshake()
                break
            except (ssl.SSLError, IOError):
                # proxystate.log.error(e.__str__())
                return

        self.rdata = HTTPSUtil.readSSL(self.peer)
        self.handle()
        

    def _getresponse(self, conn):
        res = conn.getresponse()
        body = res.read()
        if res.version == 10:
            proto = "HTTP/1.0"
        else:
            proto = "HTTP/1.1"
        code = res.status
        msg = res.reason
        headers = dict(res.getheaders())
        conn.close()
        res = HTTPResponse(proto, code, msg, headers, body)
        return res

class ThreadedHTTPProxyServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True
    pass

class ProxyServer():    
    def __init__(self, init_state):
        global proxystate
        proxystate = init_state
        self.proxyServer_port = proxystate.listenport

    def startProxyServer(self):
        global proxystate
        
        self.proxyServer_host = "0.0.0.0"
    
        self.proxyServer = ThreadedHTTPProxyServer((self.proxyServer_host, self.proxyServer_port), ProxyHandler)
        self.proxyServer.allow_reuse_address = True

        # Start a thread with the server (that thread will then spawn a worker
        # thread for each request)
        server_thread = threading.Thread(target = self.proxyServer.serve_forever)
    
        # Exit the server thread when the main thread terminates
        server_thread.setDaemon(True)
        proxystate.log.info("Server %s listening on port %d" % (self.proxyServer_host, self.proxyServer_port))
        server_thread.start()

        while True:
            time.sleep(0.1)

    def stopProxyServer(self):
        self.proxyServer.shutdown()

class ProxyState:
    def __init__(self, port = 8080):
        # Configuration options, set to default values
        self.plugin     = ProxyPlugin() # Init with a "null" plugin
        self.listenport = port
        # Internal state
        self.log        = Logger()
        self.history    = HttpHistory()
        self.redirect   = None

    @staticmethod
    def getTargetHost(req):
        global proxystate
        # Determine the target host (check if redirection is in place)
        if proxystate.redirect is None:
            target = req.getHost()
        else:
            target = proxystate.redirect

        return target

class ProxyPlugin:
    EVENT_MANGLE_REQUEST  = 1
    EVENT_MANGLE_RESPONSE = 2

    __DISPATCH_MAP = {
        EVENT_MANGLE_REQUEST:  'proxy_mangle_request',
        EVENT_MANGLE_RESPONSE: 'proxy_mangle_response',
        }

    def __init__(self, filename = None):
        self.filename = filename
    
        if filename is not None:
            import imp
            assert os.path.isfile(filename)
            self.module = imp.load_source('plugin', self.filename)
        else:
            self.module = None

    def dispatch(self, event, *args):
        if self.module is None:
            # No plugin
            return None

        assert event in ProxyPlugin.__DISPATCH_MAP
        try:
            a = getattr(self.module, ProxyPlugin.__DISPATCH_MAP[event])
        except AttributeError:
            a = None

        if a is not None:
            r = a(*args)
        else:
            r = None
            
        return r

    @staticmethod
    def delegate(event, arg):
        global proxystate

        # Allocate a history entry
        hid = proxystate.history.allocate()

        if event == ProxyPlugin.EVENT_MANGLE_REQUEST:
            proxystate.history[hid].oreq = hid

            # Process this argument through the plugin
            mangled_arg = proxystate.plugin.dispatch(ProxyPlugin.EVENT_MANGLE_REQUEST, arg.clone())

        elif event == ProxyPlugin.EVENT_MANGLE_RESPONSE:
            proxystate.history[hid].ores = hid

            # Process this argument through the plugin
            mangled_arg = proxystate.plugin.dispatch(ProxyPlugin.EVENT_MANGLE_RESPONSE, arg.clone())

        if mangled_arg is not None:
            if event == ProxyPlugin.EVENT_MANGLE_REQUEST:
                proxystate.history[hid].mreq = mangled_arg
            elif event == ProxyPlugin.EVENT_MANGLE_RESPONSE:
                proxystate.history[hid].mres = mangled_arg

            # HTTPConnection.request does the dirty work :-)
            ret = mangled_arg
        else:
            # No plugin is currently installed, or the plugin does not define
            # the proper method, or it returned None. We fall back on the
            # original argument
            ret = arg

        return ret

