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

import threading

# Synchronization decorator
def synchronized(lock):
    def wrap(f):
        def new_function(*args, **kw):
            lock.acquire()
            try:
                return f(*args, **kw)
            finally:
                lock.release()
        return new_function
    return wrap

class HttpHistoryEntry:
    def __init__(self, idz, oreq = None, mreq = None, ores = None, mres = None):
        self.id   = idz         # Entry identified (mandatory)
        self.oreq = oreq        # Original request
        self.mreq = mreq        # Edited request
        self.ores = ores        # Original response
        self.mres = mres        # Edited response

class HttpHistory:
    # Synchronization lock
    lock  = threading.Lock()

    def __init__(self):
        self.__history = []

    @synchronized(lock)
    def allocate(self):
        idz = len(self.__history)
        h = HttpHistoryEntry(idz = idz)
        self.__history.append(h)
        return idz

    @synchronized(lock)
    def __getitem__(self, idz):
        return self.__history[idz]

    def count(self):
        """
        Count requests and responses. Return a tuple (#req, #res).
        """
        nreq, nres = 0, 0
        for entry in self.__history:
            if entry.oreq is not None:
                nreq += 1
            if entry.ores is not None:
                nres += 1
        return nreq, nres

