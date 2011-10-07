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

import httplib
import ssl
import StringIO
from http import *
import select
import time

class HTTPSRequest(HTTPMessage):
    @staticmethod
    def sendAck(socket):
        # Send a 200 response to acknowledge the connection
        ack = HTTPResponse("HTTP/1.1", HTTPMessage.HTTP_CODE_OK, "Connection Established")
        socket.send(ack.serialize())

class HTTPSUtil():
    @staticmethod
    def wait_read(socket):
        if socket.pending():
            return

        select.select([socket], [], [])
    
    @staticmethod
    def readSSL(socket):
	ret_data = ''

        while True:
            try:
                ret_data += socket.read(4096)
                if not(socket.pending()):
                    break
                if 'GET' in ret_data and ret_data.count(HTTPMessage.EOL*2) == 1:
                    break
                elif 'POST' in ret_data and ret_data.count(HTTPMessage.EOL*2) == 2:
                    break
            except ssl.SSLError as err:
                if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                    self.wait_read(socket)

	return StringIO.StringIO(ret_data)

